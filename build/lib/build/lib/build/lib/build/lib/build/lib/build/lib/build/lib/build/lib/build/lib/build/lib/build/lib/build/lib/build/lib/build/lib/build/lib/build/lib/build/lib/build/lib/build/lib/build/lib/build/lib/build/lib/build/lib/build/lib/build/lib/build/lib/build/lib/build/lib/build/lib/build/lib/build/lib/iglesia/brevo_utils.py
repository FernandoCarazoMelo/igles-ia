import os

import brevo_python
import pandas as pd
from brevo_python.rest import ApiException


def brevo_get_all_emails():
    """
    Fetches all emails from Brevo contacts, save them to a CSV file (nombre,email), and returns the list of emails
    Returns:
        list: A list of email addresses.
    """
    configuration = brevo_python.Configuration()
    configuration.api_key["api-key"] = os.getenv("BREVO_TOKEN")

    api_instance = brevo_python.ContactsApi(brevo_python.ApiClient(configuration))
    try:
        # Fetch all contacts
        api_response = api_instance.get_contacts(limit=1000)
        c = api_response.contacts
        # Prepare data for CSV
        data = pd.DataFrame(
            {
                "email": [x["email"] for x in c],
                "nombre": [x["attributes"]["NOMBRE"] for x in c],
            }
        )
    except ApiException as e:
        print(f"Exception when calling ContactsApi->get_contacts: {e}")
        return []
    return data
