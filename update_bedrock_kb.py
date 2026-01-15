import boto3
import sys
import os
from dotenv import load_dotenv

load_dotenv()

if len(sys.argv) != 2:
    print("Usage: python update_bedrock_kb.py <new_source_url>")
    sys.exit(1)

new_url = sys.argv[1]

if not new_url or new_url.strip() == "":
    print("ℹ️  Empty URL provided, nothing to do")
    sys.exit(0)

kb_id = os.getenv('BEDROCK_KB_ID')
data_source_id = os.getenv('BEDROCK_DATA_SOURCE_ID')
region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
profile = os.getenv('AWS_PROFILE')

session = boto3.Session(profile_name=profile, region_name=region)
client = session.client('bedrock-agent')

current = client.get_data_source(knowledgeBaseId=kb_id, dataSourceId=data_source_id)
existing_urls = current['dataSource']['dataSourceConfiguration']['webConfiguration']['sourceConfiguration']['urlConfiguration']['seedUrls']

if any(url['url'] == new_url for url in existing_urls):
    print(f"ℹ️  URL already exists in data source: {new_url}")
    sys.exit(0)

existing_urls.append({'url': new_url})

response = client.update_data_source(
    knowledgeBaseId=kb_id,
    dataSourceId=data_source_id,
    name='knowledge-base-quick-start-u6y2h-data-source',
    dataSourceConfiguration={
        'type': 'WEB',
        'webConfiguration': {
            'crawlerConfiguration': {
                'crawlerLimits': {
                    'rateLimit': 300
                }
            },
            'sourceConfiguration': {
                'urlConfiguration': {
                    'seedUrls': existing_urls
                }
            }
        }
    }
)

print(f"✅ Added URL to data source {data_source_id}: {new_url}")
