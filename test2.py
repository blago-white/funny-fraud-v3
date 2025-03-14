from helper20sms.helper20sms import Helper20SMS, BadApiKeyProvidedException


response = Helper20SMS(api_key="bqFKsHTPW46T1J0TyXJb").get_number(service_id=19031, max_price=20)

print(response)

Helper20SMS(api_key="").set_order_status(order_id=1, status="CANCEL")
