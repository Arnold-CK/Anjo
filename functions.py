import streamlit_authenticator as stauth
from datetime import datetime


def switch_page(page_name: str):
    from streamlit.runtime.scriptrunner import RerunData, RerunException
    from streamlit.source_util import get_pages

    def standardize_name(name: str) -> str:
        return name.lower().replace("_", " ")

    page_name = standardize_name(page_name)

    pages = get_pages("Home.py")  # OR whatever your main page is called

    for page_hash, config in pages.items():
        if standardize_name(config["page_name"]) == page_name:
            raise RerunException(
                RerunData(
                    page_script_hash=page_hash,
                    page_name=page_name,
                )
            )

    page_names = [standardize_name(config["page_name"]) for config in pages.values()]

    raise ValueError(f"Could not find page {page_name}. Must be one of {page_names}")


def get_cost_categories():
    categories = [
        "Seeds and Seedlings",
        "Fertilisers and Nutrients",
        "Labour and Salaries",
        "Rent and Lease",
        "Delivery to Customer",
        "Maintenance and Repair",
        "Miscellaneous",
        "Utilities",
        "Giveaway Cost",
    ]

    categories.sort()

    return categories


def format_column(entry):
    return ' '.join(word.capitalize() for word in entry.split('_'))


def format_date(input_date):
    # Convert the input string to a datetime object
    # date_object = datetime.strptime(input_date, '%d/%m/%y')

    # Format the datetime object as required (8/Oct/2023)
    formatted_date = input_date.strftime('%d/%b/%Y')

    return formatted_date

# def hasher():
#     hashed_passwords = stauth.Hasher(["tony123", "andrew456", "MIS4l1fe"]).generate()
#     return hashed_passwords
