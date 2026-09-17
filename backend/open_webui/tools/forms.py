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
    'car_booking': {
        'formId': 'car_booking',
        'version': 1,
        'title': 'Book a Ride',
        'description': 'Provide your ride details',
        'submitLabel': 'Book Ride',
        'submitAction': 'book_ride',
        'schema': {
            'type': 'object',
            'required': ['pickupLocation', 'dropLocation', 'carType'],
            'properties': {
                'pickupLocation': {'type': 'string', 'title': 'Pickup Location'},
                'dropLocation': {'type': 'string', 'title': 'Drop Location'},
                'carType': {
                    'type': 'string',
                    'title': 'Car Type',
                    'enum': ['mini', 'sedan', 'suv', 'luxury'],
                },
                'pickupTime': {
                    'type': 'string',
                    'title': 'Pickup Time',
                    'enum': ['now', '15_minutes', '30_minutes', 'schedule_later'],
                },
                'passengers': {'type': 'integer', 'title': 'Passengers'},
                'paymentMethod': {
                    'type': 'string',
                    'title': 'Payment Method',
                    'enum': ['cash', 'card', 'wallet'],
                },
            },
        },
        'uiSchema': {
            'order': ['pickupLocation', 'dropLocation', 'carType', 'pickupTime', 'passengers', 'paymentMethod'],
            'widgets': {
                'pickupLocation': 'text',
                'dropLocation': 'text',
                'carType': 'select',
                'pickupTime': 'select',
                'passengers': 'number',
                'paymentMethod': 'select',
            },
            'enumLabels': {
                'carType': {
                    'mini': 'Mini',
                    'sedan': 'Sedan',
                    'suv': 'SUV',
                    'luxury': 'Luxury',
                },
                'pickupTime': {
                    'now': 'Right now',
                    '15_minutes': 'In 15 minutes',
                    '30_minutes': 'In 30 minutes',
                    'schedule_later': 'Schedule for later',
                },
                'paymentMethod': {
                    'cash': 'Cash',
                    'card': 'Card',
                    'wallet': 'Wallet',
                },
            },
        },
        'defaultData': {
            'carType': 'sedan',
            'pickupTime': 'now',
            'passengers': 1,
            'paymentMethod': 'card',
        },
    },
    'food_order': {
        'formId': 'food_order',
        'version': 1,
        'title': 'Order Food',
        'description': "Tell us what you'd like to order",
        'submitLabel': 'Place Order',
        'submitAction': 'place_food_order',
        'schema': {
            'type': 'object',
            'required': ['restaurant', 'items', 'deliveryAddress'],
            'properties': {
                'restaurant': {
                    'type': 'string',
                    'title': 'Restaurant',
                    'enum': ['pizza_palace', 'sushi_spot', 'burger_barn', 'curry_house'],
                },
                'items': {'type': 'string', 'title': 'Items'},
                'quantity': {'type': 'integer', 'title': 'Quantity'},
                'deliveryAddress': {'type': 'string', 'title': 'Delivery Address'},
                'paymentMethod': {
                    'type': 'string',
                    'title': 'Payment Method',
                    'enum': ['cash_on_delivery', 'card', 'upi'],
                },
                'instructions': {'type': 'string', 'title': 'Delivery Instructions'},
            },
        },
        'uiSchema': {
            'order': ['restaurant', 'items', 'quantity', 'deliveryAddress', 'paymentMethod', 'instructions'],
            'widgets': {
                'restaurant': 'select',
                'items': 'text',
                'quantity': 'number',
                'deliveryAddress': 'text',
                'paymentMethod': 'select',
                'instructions': 'text',
            },
            'enumLabels': {
                'restaurant': {
                    'pizza_palace': 'Pizza Palace',
                    'sushi_spot': 'Sushi Spot',
                    'burger_barn': 'Burger Barn',
                    'curry_house': 'Curry House',
                },
                'paymentMethod': {
                    'cash_on_delivery': 'Cash on Delivery',
                    'card': 'Card',
                    'upi': 'UPI',
                },
            },
        },
        'defaultData': {
            'quantity': 1,
            'paymentMethod': 'cash_on_delivery',
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


def _require_active_form(chat_id: Optional[str], expected_form_id: str) -> tuple[Optional[dict], Optional[str]]:
    """Look up the form instance currently open in this chat and make sure it's the expected type.

    Returns (instance, None) on success, or (None, error_message) if no form is open or a
    different form is open (relevant now that multiple form types can be active over time).
    """
    instance_id = _ACTIVE_FORM_BY_CHAT.get(chat_id)
    instance = _FORM_INSTANCES.get(instance_id) if instance_id else None
    if not instance or instance.get('formId') != expected_form_id:
        return None, (
            f'No "{expected_form_id}" form has been shown in this chat yet, or a different form is '
            f'currently open. Call show_form("{expected_form_id}") first and wait for the user to '
            f'submit it before calling this tool.'
        )
    return instance, None


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
    registered form definition. Call this FIRST, before any diagnostic/business tool, whenever the
    user reports a problem or request that this system has a matching form for (e.g. an application
    error, outage, or 5xx/4xx error -> form_id "diagnose_application"; wanting a ride/cab/taxi ->
    form_id "car_booking"; wanting to order food/a meal/delivery -> form_id "food_order") -- even if
    they already gave some details in their message; prefill what you know and let the form collect
    the rest. Do not ask the required fields one by one in chat, and do not skip straight to running
    a diagnostic or business tool without showing this form first.
    Currently supported form_id values: "diagnose_application", "car_booking", "food_order".

    :param form_id: The registered form id to render.
    :param prefill: Any field values already known from the conversation, to pre-fill the form. Omit unknown fields.
    :return: A short status string. The user's answers will arrive as a normal follow-up chat message once they submit -- do not wait synchronously for them, and do not call run_diagnostics until that follow-up message arrives.
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
    Run a (mocked) diagnostic check against an application/service and return findings. Do NOT call
    this directly from the user's initial report -- you must call show_form("diagnose_application")
    first and wait for the user's submission message. Calling this before the form has been shown
    in this chat will fail. After you get findings back, call show_result to present them as a
    result card -- do not just describe them in a plain text reply.

    :param environment: Deployment environment, e.g. "production", "staging".
    :param service: The service to diagnose, e.g. "api-gateway".
    :param error_code: The HTTP error code observed, e.g. "502".
    :param started: When the issue started, e.g. "15_minutes".
    :param recent_deployment: Whether there was a recent deployment.
    :param checks: The checks to run, e.g. ["logs", "service_health", "gateway"].
    :return: JSON with mocked diagnostic findings, or an error asking you to show the form first.
    """
    try:
        instance, error = _require_active_form(__chat_id__, 'diagnose_application')
        if error:
            return JSONCodec.dumps({'status': 'error', 'error': error}, ensure_ascii=False)
        stored = instance['data']

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


async def book_ride(
    pickup_location: Optional[str] = None,
    drop_location: Optional[str] = None,
    car_type: Optional[str] = None,
    pickup_time: Optional[str] = None,
    passengers: Optional[int] = None,
    payment_method: Optional[str] = None,
    __chat_id__: str = None,
) -> str:
    """
    Confirm a (mocked) ride booking with a driver, ETA and fare estimate. Do NOT call this directly
    from the user's initial request -- you must call show_form("car_booking") first and wait for the
    user's submission message. Calling this before the form has been shown in this chat will fail.
    After you get the booking confirmation back, call show_result to present it as a result card --
    do not just describe it in a plain text reply.

    :param pickup_location: Where to pick the rider up.
    :param drop_location: Where to drop the rider off.
    :param car_type: The vehicle tier, e.g. "sedan", "suv".
    :param pickup_time: When to pick up, e.g. "now", "15_minutes".
    :param passengers: Number of passengers.
    :param payment_method: How the ride will be paid for, e.g. "card".
    :return: JSON with a mocked booking confirmation, or an error asking you to show the form first.
    """
    try:
        instance, error = _require_active_form(__chat_id__, 'car_booking')
        if error:
            return JSONCodec.dumps({'status': 'error', 'error': error}, ensure_ascii=False)
        stored = instance['data']

        pickup_location = pickup_location or stored.get('pickupLocation')
        drop_location = drop_location or stored.get('dropLocation')
        car_type = car_type or stored.get('carType', 'sedan')
        pickup_time = pickup_time or stored.get('pickupTime', 'now')
        passengers = passengers if passengers is not None else stored.get('passengers', 1)
        payment_method = payment_method or stored.get('paymentMethod', 'card')

        # Mocked booking -- a real implementation would call a dispatch/ride-hailing API here.
        fare_per_km = {'mini': 8, 'sedan': 11, 'suv': 15, 'luxury': 25}.get(car_type, 11)
        estimated_km = 7
        booking = {
            'status': 'confirmed',
            'bookingId': f'RIDE-{uuid.uuid4().hex[:6].upper()}',
            'pickupLocation': pickup_location,
            'dropLocation': drop_location,
            'carType': car_type,
            'pickupTime': pickup_time,
            'passengers': passengers,
            'paymentMethod': payment_method,
            'driverName': 'Alex Morgan',
            'driverEtaMinutes': 4,
            'estimatedFare': fare_per_km * estimated_km,
            'summary': f'{car_type.title()} booked from {pickup_location} to {drop_location}, driver arriving in 4 minutes.',
        }

        return JSONCodec.dumps(booking, ensure_ascii=False)
    except Exception as e:
        log.exception(f'book_ride error: {e}')
        return JSONCodec.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False)


async def place_food_order(
    restaurant: Optional[str] = None,
    items: Optional[str] = None,
    quantity: Optional[int] = None,
    delivery_address: Optional[str] = None,
    payment_method: Optional[str] = None,
    instructions: Optional[str] = None,
    __chat_id__: str = None,
) -> str:
    """
    Confirm a (mocked) food order with an order id and estimated delivery time. Do NOT call this
    directly from the user's initial request -- you must call show_form("food_order") first and wait
    for the user's submission message. Calling this before the form has been shown in this chat will
    fail. After you get the order confirmation back, call show_result to present it as a result card
    -- do not just describe it in a plain text reply.

    :param restaurant: The restaurant to order from, e.g. "pizza_palace".
    :param items: Free-text description of the items ordered.
    :param quantity: Number of items/dishes ordered.
    :param delivery_address: Where to deliver the order.
    :param payment_method: How the order will be paid for, e.g. "cash_on_delivery".
    :param instructions: Optional delivery instructions.
    :return: JSON with a mocked order confirmation, or an error asking you to show the form first.
    """
    try:
        instance, error = _require_active_form(__chat_id__, 'food_order')
        if error:
            return JSONCodec.dumps({'status': 'error', 'error': error}, ensure_ascii=False)
        stored = instance['data']

        restaurant = restaurant or stored.get('restaurant')
        items = items or stored.get('items')
        quantity = quantity if quantity is not None else stored.get('quantity', 1)
        delivery_address = delivery_address or stored.get('deliveryAddress')
        payment_method = payment_method or stored.get('paymentMethod', 'cash_on_delivery')
        instructions = instructions or stored.get('instructions')

        # Mocked order -- a real implementation would call a food delivery/POS API here.
        price_per_item = {
            'pizza_palace': 12,
            'sushi_spot': 16,
            'burger_barn': 9,
            'curry_house': 13,
        }.get(restaurant, 12)
        order = {
            'status': 'confirmed',
            'orderId': f'ORD-{uuid.uuid4().hex[:6].upper()}',
            'restaurant': restaurant,
            'items': items,
            'quantity': quantity,
            'deliveryAddress': delivery_address,
            'paymentMethod': payment_method,
            'instructions': instructions,
            'total': round(price_per_item * (quantity or 1), 2),
            'estimatedDeliveryMinutes': 35,
            'summary': f'Order placed at {restaurant} for delivery to {delivery_address}, arriving in ~35 minutes.',
        }

        return JSONCodec.dumps(order, ensure_ascii=False)
    except Exception as e:
        log.exception(f'place_food_order error: {e}')
        return JSONCodec.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False)
