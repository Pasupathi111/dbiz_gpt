"""
Generic Dynamic Agentic UI / Form framework (POC).

This is a separate, reusable framework from the older HR-specific
AGENTIC_FORM_SCHEMAS / create_job / schedule_interview tools in
tools/builtin.py (which this module does not touch). It demonstrates the
full vertical slice:

    chat -> agent decides structured input is needed -> show_form
         -> user fills + submits the form as a normal chat message
         -> agent calls a business tool (run_diagnostics) with the values
         -> agent calls show_result to render a result card

Adding a new form to the system means adding an entry to FORM_REGISTRY (and,
if it needs one, a small mock/real business tool for its submitAction) --
no changes to the chat renderer or socket plumbing are required.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from open_webui.models.chats import Chats
from open_webui.utils.chat_id import is_saved_chat_id
from open_webui.utils.json_codec import JSONCodec

log = logging.getLogger(__name__)

# =============================================================================
# FORM REGISTRY
#
# JSON Schema is the source of truth for structure/validation. uiSchema only
# carries presentation hints (field order, widget kind, enum display labels)
# that JSON Schema itself doesn't express.
# =============================================================================

FORM_REGISTRY: dict[str, dict] = {
    'diagnose_application': {
        'formId': 'diagnose_application',
        'version': 1,
        'title': 'Diagnose Application',
        'description': 'Provide details about the incident',
        'submitLabel': 'Diagnose',
        'submitAction': 'run_diagnostics',
        'schema': {
            'type': 'object',
            'required': ['environment', 'service'],
            'properties': {
                'environment': {
                    'type': 'string',
                    'title': 'Environment',
                    'enum': ['production', 'staging', 'development'],
                },
                'service': {
                    'type': 'string',
                    'title': 'Service',
                    'enum': ['api-gateway', 'auth-service', 'payments-service', 'database'],
                },
                'errorCode': {'type': 'string', 'title': 'Error Code'},
                'started': {
                    'type': 'string',
                    'title': 'Started',
                    'enum': ['5_minutes', '15_minutes', '30_minutes', '1_hour', 'unknown'],
                },
                'recentDeployment': {'type': 'boolean', 'title': 'Recent Deployment'},
                'checks': {
                    'type': 'array',
                    'title': 'Checks',
                    'items': {
                        'type': 'string',
                        'enum': ['logs', 'service_health', 'gateway'],
                    },
                },
            },
        },
        'uiSchema': {
            'order': ['environment', 'service', 'errorCode', 'started', 'recentDeployment', 'checks'],
            'widgets': {
                'environment': 'select',
                'service': 'select',
                'errorCode': 'text',
                'started': 'select',
                'recentDeployment': 'radio',
                'checks': 'checkboxes',
            },
            'enumLabels': {
                'environment': {
                    'production': 'Production',
                    'staging': 'Staging',
                    'development': 'Development',
                },
                'service': {
                    'api-gateway': 'API Gateway',
                    'auth-service': 'Auth Service',
                    'payments-service': 'Payments Service',
                    'database': 'Database',
                },
                'started': {
                    '5_minutes': '5 minutes ago',
                    '15_minutes': '15 minutes ago',
                    '30_minutes': '30 minutes ago',
                    '1_hour': '1 hour ago',
                    'unknown': 'Not sure',
                },
                'checks': {
                    'logs': 'Check application logs',
                    'service_health': 'Check service health',
                    'gateway': 'Check gateway',
                },
            },
        },
        'defaultData': {
            'environment': 'production',
            'service': 'api-gateway',
            'started': '15_minutes',
            'recentDeployment': False,
            'checks': ['logs', 'service_health', 'gateway'],
        },
    },
}

# In-memory instance + "active form per chat" tracking -- a POC substitute for
# a real table, matching the pattern already used for _AGENTIC_FORM_RECORDS in
# tools/builtin.py. Not meant to survive a process restart.
_FORM_INSTANCES: dict[str, dict] = {}
_ACTIVE_FORM_BY_CHAT: dict[str, str] = {}


def _new_instance_id(form_id: str) -> str:
    return f'{form_id}-{uuid.uuid4().hex[:8]}'


async def _persist_message_data(chat_id: Optional[str], message_id: Optional[str], data: dict) -> None:
    if is_saved_chat_id(chat_id) and message_id:
        try:
            await Chats.upsert_message_to_chat_by_id_and_message_id(
                chat_id, message_id, {'data': data}, touch=False
            )
        except Exception as e:
            log.warning(f'Failed to persist form message data: {e}')


def _build_form_message_data(instance_id: str, form_id: str, data: dict, status: str = 'ACTIVE') -> dict:
    definition = FORM_REGISTRY[form_id]
    return {
        'type': 'FORM',
        'formId': form_id,
        'formInstanceId': instance_id,
        'status': status,
        'payload': {
            'title': definition['title'],
            'description': definition.get('description', ''),
            'submitLabel': definition.get('submitLabel', 'Submit'),
            'schema': definition['schema'],
            'uiSchema': definition.get('uiSchema', {}),
            'data': data,
        },
    }


async def show_form(
    form_id: str,
    prefill: Optional[dict] = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Render an interactive structured form inside the chat for the user to fill in, based on a
    registered form definition. Use this whenever completing the user's request requires several
    pieces of structured information (e.g. diagnosing an application error). Do not ask the
    required fields one by one in chat -- call this tool and let the form collect them.
    Currently supported form_id values: "diagnose_application".

    :param form_id: The registered form id to render.
    :param prefill: Any field values already known from the conversation, to pre-fill the form. Omit unknown fields.
    :return: A short status string. The user's answers will arrive as a normal follow-up chat message once they submit -- do not wait synchronously for them.
    """
    try:
        definition = FORM_REGISTRY.get(form_id)
        if not definition:
            return JSONCodec.dumps({'status': 'error', 'error': f'Unknown form_id: {form_id}'}, ensure_ascii=False)

        instance_id = _new_instance_id(form_id)
        data = {**definition.get('defaultData', {}), **(prefill or {})}

        _FORM_INSTANCES[instance_id] = {
            'chatId': __chat_id__,
            'messageId': __message_id__,
            'formId': form_id,
            'data': data,
        }
        if __chat_id__:
            _ACTIVE_FORM_BY_CHAT[__chat_id__] = instance_id

        message_data = _build_form_message_data(instance_id, form_id, data)
        await _persist_message_data(__chat_id__, __message_id__, message_data)

        if __event_emitter__:
            await __event_emitter__({'type': 'FORM', 'data': message_data})

        return JSONCodec.dumps(
            {
                'status': 'shown',
                'formInstanceId': instance_id,
                'message': 'Form displayed to the user; wait for their submission as the next chat message.',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'show_form error: {e}')
        return JSONCodec.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False)


async def update_active_form(
    patch: dict,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
) -> str:
    """
    Update one or more field values on the form that is currently open in this chat, in place --
    without opening a second form. Use this when the user corrects or changes an answer in natural
    language while a form is still on screen (e.g. "actually this is staging").

    :param patch: A dict of {field_name: new_value} for the fields to change, using the same field names as the open form's schema.
    :return: JSON with the updated field values, or an error if no form is currently open in this chat.
    """
    try:
        instance_id = _ACTIVE_FORM_BY_CHAT.get(__chat_id__)
        instance = _FORM_INSTANCES.get(instance_id) if instance_id else None
        if not instance:
            return JSONCodec.dumps(
                {'status': 'error', 'error': 'No form is currently open in this chat.'}, ensure_ascii=False
            )

        instance['data'] = {**instance['data'], **(patch or {})}

        message_data = _build_form_message_data(instance_id, instance['formId'], instance['data'])
        await _persist_message_data(instance.get('chatId'), instance.get('messageId'), message_data)

        if __event_emitter__:
            await __event_emitter__(
                {
                    'type': 'FORM_UPDATE',
                    'data': {**message_data, 'targetMessageId': instance.get('messageId')},
                }
            )

        return JSONCodec.dumps({'status': 'updated', 'data': instance['data']}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'update_active_form error: {e}')
        return JSONCodec.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False)


async def show_result(
    title: str,
    summary: str,
    checks_completed: Optional[list[str]] = None,
    details: Optional[str] = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Render a result card inside the chat summarizing the outcome of an action or tool run (e.g.
    after running diagnostics). Use this after completing a task that started from a dynamic form,
    to give the user a clear, structured summary.

    :param title: Short result card title, e.g. "Diagnosis".
    :param summary: One or two sentence summary of the outcome.
    :param checks_completed: List of short labels for checks/steps that were completed.
    :param details: Optional longer free-text details shown behind a "View Details" toggle.
    :return: A short confirmation string.
    """
    try:
        instance_id = _ACTIVE_FORM_BY_CHAT.get(__chat_id__)

        message_data = {
            'type': 'RESULT',
            'formInstanceId': instance_id,
            'status': 'SUCCESS',
            'result': {
                'title': title,
                'summary': summary,
                'checksCompleted': checks_completed or [],
                'details': details or '',
            },
        }

        await _persist_message_data(__chat_id__, __message_id__, message_data)

        if __event_emitter__:
            await __event_emitter__({'type': 'RESULT', 'data': message_data})

        if __chat_id__ in _ACTIVE_FORM_BY_CHAT:
            del _ACTIVE_FORM_BY_CHAT[__chat_id__]

        return JSONCodec.dumps({'status': 'shown'}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'show_result error: {e}')
        return JSONCodec.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False)


# =============================================================================
# MOCK BUSINESS TOOL (POC substitute for a real diagnostic integration)
# =============================================================================


async def run_diagnostics(
    environment: Optional[str] = None,
    service: Optional[str] = None,
    error_code: Optional[str] = None,
    started: Optional[str] = None,
    recent_deployment: Optional[bool] = None,
    checks: Optional[list[str]] = None,
    __chat_id__: str = None,
) -> str:
    """
    Run a (mocked) diagnostic check against an application/service and return findings. Call this
    after the user has submitted the "Diagnose Application" form, using the values from their
    submission message.

    :param environment: Deployment environment, e.g. "production", "staging".
    :param service: The service to diagnose, e.g. "api-gateway".
    :param error_code: The HTTP error code observed, e.g. "502".
    :param started: When the issue started, e.g. "15_minutes".
    :param recent_deployment: Whether there was a recent deployment.
    :param checks: The checks to run, e.g. ["logs", "service_health", "gateway"].
    :return: JSON with mocked diagnostic findings.
    """
    try:
        instance_id = _ACTIVE_FORM_BY_CHAT.get(__chat_id__)
        instance = _FORM_INSTANCES.get(instance_id) if instance_id else None
        stored = instance['data'] if instance else {}

        environment = environment or stored.get('environment')
        service = service or stored.get('service')
        checks = checks if checks is not None else stored.get('checks', [])

        # Mocked findings -- a real implementation would call logging/monitoring APIs here.
        unhealthy = service in {'api-gateway', 'auth-service'}
        findings = {
            'status': 'unhealthy' if unhealthy else 'healthy',
            'environment': environment,
            'service': service,
            'errorCode': error_code,
            'checksCompleted': checks,
            'summary': f"{service or 'The service'} appears {'unhealthy' if unhealthy else 'healthy'}.",
        }

        return JSONCodec.dumps(findings, ensure_ascii=False)
    except Exception as e:
        log.exception(f'run_diagnostics error: {e}')
        return JSONCodec.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False)
