import re

def refactor_to_async(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Imports
    content = content.replace("from playwright.sync_api import sync_playwright", "import asyncio\nfrom playwright.async_api import async_playwright")

    # 2. Function definitions
    content = content.replace("def upload_youtube(", "async def upload_youtube(")
    content = content.replace("def upload_instagram(", "async def upload_instagram(")
    content = content.replace("def main():", "async def main():")

    # 3. time.sleep
    content = content.replace("time.sleep(", "await asyncio.sleep(")

    # 4. Await Playwright actions
    # We use regex to find method calls that return promises in async_api
    
    methods_to_await = [
        r'\.click\(', r'\.fill\(', r'\.set_input_files\(', r'\.is_visible\(',
        r'\.count\(', r'\.text_content\(', r'\.type\(', r'\.press\(', r'\.clear\(',
        r'\.goto\(', r'\.wait_for_selector\(', r'\.set_files\('
    ]
    
    # We must be careful not to double await.
    # A simple regex substitution: find `obj.method(` and replace with `await obj.method(`
    # This is tricky because we only want to await locator actions, not string methods like .strip()
    
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'def ' in line or 'import ' in line or '#' in line and not line.strip().startswith('#'):
            # Only process lines that are purely code to be safe
            pass
            
        # Await locator methods
        for method in methods_to_await:
            # Look for something that isn't already awaited
            pattern = r'(?<!await )(\b[\w_.]+' + method + r')'
            line = re.sub(pattern, r'await \1', line)
            
        new_lines.append(line)
        
    content = '\n'.join(new_lines)
    
    # 5. expect_file_chooser
    content = content.replace("with page.expect_file_chooser", "async with page.expect_file_chooser")
    
    # 6. context.new_page
    content = content.replace("context.new_page()", "await context.new_page()")
    
    # 7. async_playwright block in main
    content = content.replace("with sync_playwright() as p:", "async with async_playwright() as p:")
    content = content.replace("p.chromium.launch_persistent_context", "await p.chromium.launch_persistent_context")
    
    # 8. Parallel execution in main
    # We need to replace the sequential calls with asyncio.gather
    # Find the execution block
    main_body = """
        tasks = []
        if do_youtube:
            print("\\n🔴 YouTube Upload (Queued)")
            tasks.append(upload_youtube(context, config, video_path))

        if do_instagram:
            print("\\n🟣 Instagram Upload (Queued)")
            tasks.append(upload_instagram(context, config, video_path))
            
        if tasks:
            print("\\n🚀 Launching parallel uploads...")
            await asyncio.gather(*tasks)

        print("\\n✅ All done! Browser tabs will stay open for review.")
        print("-" * 40)
        
        # Keep context open to let user review
        while True:
            await asyncio.sleep(1)
"""
    
    # Replace the old execution block (lines 538 to end of main)
    # This might be tricky with regex, let's write it carefully.

    with open(filepath + '.new.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    refactor_to_async('c:/Users/ASMIT/Desktop/MyProjects/Reelix/uploader.py')
