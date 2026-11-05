import sys
from crawl import crawl_site_async
import asyncio
from json_report import write_json_report

async def main():

    num_of_argv = len(sys.argv)
    if num_of_argv < 2:
        print("no website provided")
        sys.exit(1)
    elif num_of_argv == 2:
        max_concurrency = 5  
        max_pages = 100      
    elif num_of_argv == 3:
        max_concurrency = int(sys.argv[2])
        max_pages = 100      
    elif num_of_argv == 4:
        max_concurrency = int(sys.argv[2])
        max_pages = int(sys.argv[3])
    else:
        print("too many arguments provided")
        sys.exit(1)

    base_url = sys.argv[1]
    print(f"starting crawl of: {base_url}")


    page_data = await crawl_site_async(base_url, max_concurrency, max_pages)

    write_json_report(page_data)

if __name__ == "__main__":
    asyncio.run(main())



