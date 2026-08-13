import requests
import json
import os

# Upwork API Access Token and GraphQL Endpoint
ACCESS_TOKEN = "oauth2v2_ee124f90b0a4945ebeeb15b117eedd0f"
GRAPHQL_ENDPOINT = "https://api.upwork.com/graphql"

# Get Job ID from user input
TARGET_JOB_ID = input("Enter the Job ID to search: ")

# Required Skills for Filtering
SKILLS_REQUIRED = {skill.lower() for skill in [
    "Python", "GCP", "AWS", "SQL", "OpenAI", "API", "Spark", "Bigquery", "Serverless", "Lambda",
    "Glue", "CI/CD", "Gitlab", "Github", "Github Actions", "Programming", "Data-analytics", "Looker"
]}

# Not Required Skills for Exclusion
NOT_REQUIRED_SKILLS = {skill.lower() for skill in [
    "asp.net", ".net-framework", "php", "reactjs"
]}

# Global List to Store Jobs (instead of writing to a JSON file)
all_jobs_list = []

# GraphQL Query to Fetch Job Listings
query_fetch_jobs = """
query marketplaceJobPostingsSearch (
  $marketPlaceJobFilter: MarketplaceJobPostingsSearchFilter,
  $searchType: MarketplaceJobPostingSearchType,
  $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]
) {
  marketplaceJobPostingsSearch(
    marketPlaceJobFilter: $marketPlaceJobFilter,
    searchType: $searchType,
    sortAttributes: $sortAttributes
  ) {
    totalCount
    edges {
      node {
        id
        title
        description
        ciphertext
        skills {
          name
        }
        duration
        durationLabel
        engagement
        amount {
          currency  
        }
        recordNumber
        category
        subcategory
        freelancersToHire
        enterprise
        relevanceEncoded
        totalApplicants
        preferredFreelancerLocation
        preferredFreelancerLocationMandatory
        premium
        clientNotSureFields
        clientPrivateFields
        applied
        createdDateTime
        publishedDateTime
        renewedDateTime
        client {
          totalHires
          totalPostedJobs
          verificationStatus
          location {
            country
            state
            city
            timezone
          }
          totalReviews
          totalFeedback
          companyName
          companyRid
          hasFinancialPrivacy
          lastContractTitle
          lastContractPlatform
        }
        occupations {
          category {
            id
            prefLabel
          }
          subCategories {
            id
            prefLabel
          }
          occupationService {
            id
            prefLabel
          }
        }
        hourlyBudgetType
        hourlyBudgetMin {
          currency  
        }
        hourlyBudgetMax {
          currency 
        }
        localJobUserDistance
        weeklyBudget {
          currency  
        }
        totalFreelancersToHire
        teamId
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

# Query to Fetch Job Activity Details
query_fetch_activity = """
query getJobDetails($jobId: ID!) {
  marketplaceJobPosting(id: $jobId) {
    id
    content {
      title
      description
    }
    activityStat {
      jobActivity {
        lastClientActivity
        invitesSent
        totalInvitedToInterview
        totalHired
        totalUnansweredInvites
        totalOffered
        totalRecommended
      }
    }
  }
}
"""

# Function to send GraphQL requests
def send_graphql_request(query, variables=None):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.post(GRAPHQL_ENDPOINT, headers=headers, json={"query": query, "variables": variables})
    
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print(" GraphQL Errors:", json.dumps(data["errors"], indent=2))
            return None
        return data
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

# Fetch and Paginate Job Listings
offset = 0
found = False

while offset is not None and not found:
    print(f"Fetching next page with offset: {offset}")
    variables = {"searchType": "USER_JOBS_SEARCH", "marketPlaceJobFilter": {"pagination_eq": {"after": f"{offset}", "first": 100}}}
    job_data = send_graphql_request(query_fetch_jobs, variables)
    
    # Skip the processing if job_data is None (error handling)
    if job_data is None:
        break
    
    jobs = job_data.get("data", {}).get("marketplaceJobPostingsSearch", {}).get("edges", [])
    
    for job in jobs:
        job_node = job["node"]
        job_id = job_node["id"]
        job_skills = {skill["name"].lower() for skill in job_node.get("skills", [])}
        
        # Check if job matches the required skills and does NOT contain excluded skills
        if SKILLS_REQUIRED.intersection(job_skills) and not NOT_REQUIRED_SKILLS.intersection(job_skills):
            # Fetch activity stats for matched job
            activity_data = send_graphql_request(query_fetch_activity, {"jobId": job_id})
            if activity_data:
                job_node["activityStat"] = activity_data.get("data", {}).get("marketplaceJobPosting", {}).get("activityStat", {})

            # Handling the 'experienceLevel' being None
            if job_node.get("experienceLevel") is None:
                job_node["experienceLevel"] = "Not Available"  # Default value for experience level

            # Add job to global list instead of writing to JSON
            all_jobs_list.append(job_node)
        
        # Stop execution if the target job ID is found
        if job_id == TARGET_JOB_ID:
            print(f"Found Job ID {job_id}, stopping search.")
            found = True
            break
    
    if found:
        break
    
    page_info = job_data.get("data", {}).get("marketplaceJobPostingsSearch", {}).get("pageInfo", {})
    offset = int(page_info.get("endCursor")) if page_info.get("hasNextPage", False) else None

print("Pagination complete.")
print(f"Total jobs collected: {len(all_jobs_list)}")
# Printing the final list of jobs
print(json.dumps(all_jobs_list, indent=2))
