import rs_classes.async_request_client as rs
import pandas as pd
import datetime
import asyncio
import copy


TOKEN = input("Please enter your Rossum API token: ")
DOMAIN = input("Please enter Rossum domain url without /v1: ")
ORGANZATION_ID = input("What is the target Organization ID: ")
ORGANIZATION = f"{DOMAIN}/v1/organizations/{ORGANZATION_ID}"
UPLOAD_FILE_PATH = input("Provide a path to load file: ")
UPLOAD_F_SHEET_NAME = input("Provide a sheet name to load file: ")
SUPPORTED_COLUMNS = {
    "auth_type": "",
    "email": "",
    "first_name": "",
    "last_name": "",
    "oidc_id": "",
    "role": "",
    "queue_ids": "",
    "can_approve": "",
}


async def main():
    client = rs.AsyncRequestClient(token=TOKEN, domain=DOMAIN)

    logger = Logger()

    df = read_template(UPLOAD_FILE_PATH, UPLOAD_F_SHEET_NAME)
    try:
        active_users, org_groups, org_queues = await collect_data(client)
    except:
        print("Can't get data")
        raise ()

    for index, row in df.iterrows():
        if index in [0]:
            continue

        user_data = prepare_user_data(row, org_groups, org_queues)

        if user_data["auth_type"] not in ["sso", "password"] or not user_data["email"]:
            print(f"Check user data entry - {user_data['email']}")
            logger.add("Error-check user data entry. No required fields.", **user_data)
            continue

        if row["email"].lower() in [
            user["email"].lower().strip() for user in active_users
        ]:
            print(f"User Exists - {user_data['email']}")
            logger.add("Skipped-User Exists", **user_data)
            continue

        print("Creating User: ", user_data["email"])
        print(user_data, type(user_data))

        try:
            response = await client.create_new_user(user_data)

            logger.add(f"User created - {response}", **user_data)
            print(f"User created - {response}")
        except:
            print(f"HTTP error- {response}")
            logger.add(f"Error - user not created - {response}", **user_data)
            continue

        if user_data["auth_type"] == "password":
            try:
                response = await client.reset_password(user_data["email"])
                logger.add(f"Password reset - {response}", **user_data)
                print(f"Password reset is done - {response}")
            except:
                print(f"HTTP error - {response}")
                logger.add(f"Error - password reset failed - {response}", **user_data)

    log_path_list = UPLOAD_FILE_PATH.split("/")[:-1]
    if len(log_path_list) > 0:
        log_path = "/".join(log_path_list) + "/"
    else:
        log_path = ""
    logger.export_log(f"{log_path}user_load_{datetime.datetime.now()}")


## Supporting code


def get_supported_columns():
    return copy.deepcopy(SUPPORTED_COLUMNS)


def prepare_user_data(row, org_groups: list, org_queues: list) -> dict:
    supported_columns = get_supported_columns()

    for column in range(len(row)):
        if pd.isna(row.iloc[column]):
            row.iloc[column] = ""
        else:
            row.iloc[column] = row.iloc[column].strip()

    supported_columns["oidc_id"] = row["oidc_id"] if row["oidc_id"] else row["email"]
    supported_columns["auth_type"] = row["auth_type"]
    supported_columns["username"] = row["email"]
    supported_columns["email"] = row["email"]
    supported_columns["first_name"] = row["first_name"]
    supported_columns["last_name"] = row["last_name"]
    supported_columns["organization"] = ORGANIZATION

    groups = []
    Admin_group = ""

    for group in org_groups:
        if group["name"] == "admin":
            Admin_group = group["url"]

        if group["name"] == "approver":
            approver_group_url = group["url"]

        if group["name"] == row["role"]:
            groups.append(group["url"])

        if (
            row["can_approve"] == "yes"
            and group["name"] == "approver"
            and group["url"] not in groups
        ):
            groups.append(group["url"])

    if len(groups) == 0:
        groups.append(approver_group_url)

    supported_columns["groups"] = groups

    queues = []

    if Admin_group not in groups:
        for queue in org_queues:
            user_queues = str(row["queue_ids"])
            user_queue_list = user_queues.split("\n")
            for q in user_queue_list:
                if str(queue["id"]) == q:
                    queues.append(queue["url"])
        if not queues:
            print("No queue assignment will be done")
    supported_columns["queues"] = queues

    # cleaning unnecessary columns
    del supported_columns["role"]
    del supported_columns["queue_ids"]
    del supported_columns["can_approve"]

    return supported_columns


def read_template(file_path: str, sheet_name: str) -> pd.DataFrame:
    supported_columns = get_supported_columns()

    try:
        df = pd.read_excel(UPLOAD_FILE_PATH, UPLOAD_F_SHEET_NAME, header=0, dtype=str)
    except:
        print("Can't read excel")
        raise ()

    if all(column in df.columns for column in supported_columns.keys()):
        print("All supported columns detected. Moving on")
        return df
    else:
        print("check columns -> ", supported_columns)
        raise ()


async def check_existing_users(client: rs.AsyncRequestClient) -> list:
    users = await client.get_all_users()
    actual_users = []
    for user in users:
        if user["deleted"] == False:
            actual_users.append(
                {
                    "id": user["id"],
                    "email": user["username"],
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "groups": user["groups"],
                    "queues": user["queues"],
                }
            )
    return actual_users


class Logger:
    def __init__(self):
        self.log = []

    def add(self, note, **kwargs):
        message = {}
        message["Messages"] = note
        message["timestamp"] = datetime.datetime.now()

        for key, value in kwargs.items():
            message[key] = value

        self.log.append(message)

    def get(self):
        return self.log

    def export_log(self, path):
        df = pd.DataFrame(self.log)
        df.to_excel(f"{path}.xlsx", index=False)


async def collect_data(client: rs.AsyncRequestClient):
    results = await asyncio.gather(
        check_existing_users(client), client.get_all_groups(), client.get_all_queues()
    )
    return results


if __name__ == "__main__":
    asyncio.run(main())
