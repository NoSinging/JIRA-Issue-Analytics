import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime

def fetch_jira_issues(jira_url, project_key, auth_email, api_token, jql_query=None):
    """
    Fetch issues from the Jira REST API.

    Parameters:
        jira_url (str): Base URL of the Jira instance (e.g., https://your-domain.atlassian.net).
        project_key (str): Project key for which issues will be fetched.
        auth_email (str): Email address of the user for authentication.
        api_token (str): API token for authentication.
        jql_query (str): Optional JQL query for filtering issues.

    Returns:
        list: List of issues returned from Jira.
    """
    endpoint = f"{jira_url}/rest/api/3/search"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # JQL for querying issues
    if jql_query is None:
        jql_query = f"project = {project_key} ORDER BY created DESC"

    params = {
        "jql": jql_query,
        "maxResults": 50,  # Adjust the number of results per page as needed
    }

    # Authenticate with basic auth using email and API token
    auth = HTTPBasicAuth(auth_email, api_token)

    try:
        response = requests.get(endpoint, headers=headers, params=params, auth=auth)
        response.raise_for_status()

        # Parse the JSON response
        issues = response.json()["issues"]
        return issues

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Jira issues: {e}")
        return []

def fetch_issue_history(jira_url, issue_key, auth_email, api_token):
    """
    Fetch the history of a specific Jira issue.

    Parameters:
        jira_url (str): Base URL of the Jira instance.
        issue_key (str): Key of the issue to fetch history for.
        auth_email (str): Email address of the user for authentication.
        api_token (str): API token for authentication.

    Returns:
        list: List of history items for the issue.
    """
    endpoint = f"{jira_url}/rest/api/3/issue/{issue_key}/changelog"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Authenticate with basic auth using email and API token
    auth = HTTPBasicAuth(auth_email, api_token)

    try:
        response = requests.get(endpoint, headers=headers, auth=auth)
        response.raise_for_status()

        # Parse the JSON response
        changelog = response.json()["values"]
        return changelog

    except requests.exceptions.RequestException as e:
        print(f"Error fetching issue history for {issue_key}: {e}")
        return []

def calculate_time_in_status(history, created_date):
    """
    Calculate the time spent in each status based on the issue history.

    Parameters:
        history (list): A list of dictionaries containing history items for the issue.
                        Each dictionary should have a "created" timestamp and "items"
                        that describe field changes, including status transitions.
        created_date (str): The creation date of the issue in ISO 8601 format.

    Returns:
        dict: A dictionary with statuses as keys and time spent (in hours) as values.
    """
    status_times = {}
    last_status = "To Do"
    last_timestamp = datetime.strptime(created_date, "%Y-%m-%dT%H:%M:%S.%f%z")

    for item in history:
        for change in item['items']:
            if change['field'] == 'status':
                created = datetime.strptime(item['created'], "%Y-%m-%dT%H:%M:%S.%f%z")
                from_status = change.get('fromString', None)
                to_status = change.get('toString', None)

                if last_status and last_timestamp:
                    time_spent = (created - last_timestamp).total_seconds() / 3600
                    status_times[last_status] = status_times.get(last_status, 0) + time_spent

                last_status = to_status
                last_timestamp = created

    # Handle the time spent in the last status
    if last_status and last_timestamp:
        now = datetime.now(last_timestamp.tzinfo)
        time_spent = (now - last_timestamp).total_seconds() / 3600
        status_times[last_status] = status_times.get(last_status, 0) + time_spent

    return status_times

# Example usage
if __name__ == "__main__":
    # Replace with your Jira instance details
    JIRA_URL = "https://your-domain.atlassian.net"
    PROJECT_KEY = "TEST"
    AUTH_EMAIL = "your-email@example.com"
    API_TOKEN = "your-api-token"

    issues = fetch_jira_issues(JIRA_URL, PROJECT_KEY, AUTH_EMAIL, API_TOKEN)

    if issues:
        print("Fetched issues:")
        for issue in issues:
            issue_key = issue['key']
            summary = issue['fields']['summary']
            status = issue['fields']['status']['name']
            created_date = issue['fields']['created']
            print(f"- {issue_key}: {summary} (Created: {created_date}, Current Status: {status})")

            # Fetch and display issue history for status changes only
            history = fetch_issue_history(JIRA_URL, issue_key, AUTH_EMAIL, API_TOKEN)
            print("  Status Change History:")

            # Include the created date with the initial "To Do" status
            print(f"    - {created_date}: None → To Do")

            status_history = []
            for item in history:
                for change in item['items']:
                    if change['field'] == 'status':
                        created = item['created']
                        from_status = change.get('fromString', 'Unknown')
                        to_status = change.get('toString', 'Unknown')
                        status_history.append((created, from_status, to_status))
                        print(f"    - {created}: {from_status} → {to_status}")

            # Calculate and display time spent in each status
            times_in_status = calculate_time_in_status(history, created_date)
            print("  Time Spent in Each Status:")
            for status, hours in times_in_status.items():
                print(f"    - {status}: {hours:.2f} hours")

            print()  # Add spacing for clarity
    else:
        print("No issues found or an error occurred.")
