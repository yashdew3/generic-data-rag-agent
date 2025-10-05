#!/usr/bin/env python3
"""
Test script to verify the RAG chat functionality.
"""
import requests
import json

def test_chat_endpoint():
    """Test the chat endpoint with a simple query"""
    url = "http://127.0.0.1:8000/api/chat"
    
    # Test data
    test_query = {
        "query": "What data is available in the uploaded files?",
        "top_k": 5,
        "file_ids": None
    }
    
    try:
        print("Testing chat endpoint...")
        print(f"URL: {url}")
        print(f"Query: {test_query['query']}")
        
        response = requests.post(url, json=test_query, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"Answer: {result.get('answer', 'No answer')}")
            print(f"Sources found: {len(result.get('sources', []))}")
            
            if result.get('sources'):
                print("Source details:")
                for i, source in enumerate(result['sources'][:3]):  # Show first 3 sources
                    print(f"  {i+1}. Collection: {source.get('collection', 'Unknown')}")
                    print(f"     Distance: {source.get('distance', 'N/A')}")
                    print(f"     Preview: {source.get('document', '')[:100]}...")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_files_endpoint():
    """Test the files endpoint to see uploaded files"""
    url = "http://127.0.0.1:8000/api/files"
    
    try:
        print("\nTesting files endpoint...")
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Files endpoint working!")
            print(f"Uploaded files: {len(result.get('files', []))}")
            
            if result.get('files'):
                print("File details:")
                for file_info in result['files'][:5]:  # Show first 5 files
                    print(f"  - {file_info.get('original_name', 'Unknown')} "
                          f"({file_info.get('file_type', 'Unknown type')})")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🚀 Testing RAG Chat System")
    print("=" * 50)
    
    # Test files endpoint first
    test_files_endpoint()
    
    # Test chat endpoint
    test_chat_endpoint()
    
    print("\n" + "=" * 50)
    print("Test completed!")