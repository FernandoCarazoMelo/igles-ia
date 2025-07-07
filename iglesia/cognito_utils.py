import boto3
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Lista ampliada de nombres compuestos comunes
COMMON_COMPOUND_NAMES = {
    # Masculinos
    "juan pablo", "juan carlos", "juan josé", "juan manuel", "juan antonio",
    "josé luis", "josé manuel", "josé antonio", "josé carlos", "josé maría",
    "luis miguel", "luis fernando", "miguel ángel", "carlos alberto", "pedro josé",
    "ángel david", "carlos andrés", "juan andrés", "jose ángel", "jose fernando",
    "juan gabriel", "josé andrés", "francisco javier", "juan francisco",

    # Femeninos
    "maría josé", "maría jesús", "maría fernanda", "maría elena", "maría teresa",
    "maría isabel", "maría eugenia", "maría luisa", "maría dolores", "maría del mar",
    "ana belén", "ana maría", "ana isabel", "ana sofía", "ana laura", "ana paula",
    "rosa maría", "laura sofía", "maría de los ángeles", "maría del carmen",
    "maría josefa", "maría auxiliadora", "maría concepción", "maría mercedes",
    "maría cristina", "maría inés", "maría gloria"
}

def extract_first_name(full_name):
    """
    Extracts the first name from a full name, respecting common Spanish compound names.
    """
    if not full_name:
        return ""

    parts = full_name.strip().lower().split()

    if len(parts) >= 2:
        candidate = f"{parts[0]} {parts[1]}"
        if candidate in COMMON_COMPOUND_NAMES:
            return candidate.title()

    return parts[0].capitalize()

def cognito_get_verified_emails(only_verified: bool = False):
    """
    Fetches all Cognito users with verified email addresses,
    and returns a DataFrame with columns ['nombre', 'email'].

    Returns:
        pd.DataFrame: Verified users with email and first name
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
            
            if only_verified and attrs.get("email_verified") == "true":
                email = attrs.get("email")
                full_name = attrs.get("name", "")
                first_name = extract_first_name(full_name)

                if email:
                    names.append(first_name)
                    emails.append(email)
            elif not only_verified:
                email = attrs.get("email")
                full_name = attrs.get("name", "")
                first_name = extract_first_name(full_name)

                if email:
                    names.append(first_name)
                    emails.append(email)
            else:
                print(f"Skipping user {user['Username']} due to unverified email.")

    df = pd.DataFrame({"nombre": names, "email": emails})
    return df


if __name__ == "__main__":
    # Example usage
    df = cognito_get_verified_emails()
    print(df.head())
    # Optionally, save to CSV
    df.to_csv("cognito_emails.csv", index=False)
    print("Emails saved to cognito_emails.csv")
