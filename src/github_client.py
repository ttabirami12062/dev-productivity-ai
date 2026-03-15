import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_pull_requests(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=20"
    response = requests.get(url, headers=headers)
    return response.json()

def get_commits(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=20"
    response = requests.get(url, headers=headers)
    return response.json()

def get_contributors(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
    response = requests.get(url, headers=headers)
    return response.json()

if __name__ == "__main__":
    # Test with your own GitHub repo
    owner = "ttabirami12062"
    repo = "IPMS"
    
    print("Fetching pull requests...")
    prs = get_pull_requests(owner, repo)
    print(f"Found {len(prs)} pull requests")
    
    print("Fetching commits...")
    commits = get_commits(owner, repo)
    print(f"Found {len(commits)} commits")
    
    print("Fetching contributors...")
    contributors = get_contributors(owner, repo)
    print(f"Found {len(contributors)} contributors")
    
    print("\nGitHub connection working!")