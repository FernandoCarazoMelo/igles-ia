import boto3
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def cognito_get_verified_emails():
    """
    Fetches all Cognito users with verified email addresses,
    and returns a DataFrame with columns ['nombre', 'email'].

    Returns:
        pd.DataFrame: Verified users with email and name
    """
    USER_POOL_ID = os.getenv("USER_POOL_ID")
    REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")

    if not USER_POOL_ID:
        raise ValueError("USER_POOL_ID is not defined")

    client = boto3.client("cognito-idp", region_name=REGION)

    paginator = client.get_paginator("list_users")
    page_iterator = paginator.paginate(UserPoolId=USER_POOL_ID)

    names = []
    emails = []

    for page in page_iterator:
        for user in page["Users"]:
            attrs = {attr["Name"]: attr["Value"] for attr in user["Attributes"]}

            if attrs.get("email_verified") == "true":
                email = attrs.get("email")
                name = attrs.get("name", "")
                if email:
                    names.append(name)
                    emails.append(email)

    df = pd.DataFrame({"nombre": names, "email": emails})
    return df


if __name__ == "__main__":
    # Example usage
    df = cognito_get_verified_emails()
    print(df.head())
    # Optionally, save to CSV
    df.to_csv("cognito_emails.csv", index=False)
    print("Emails saved to cognito_emails.csv")
