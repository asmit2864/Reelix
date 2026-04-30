import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into sections
    parts = re.split(r'# ─────────────────────────────────────────────', content)
    
    if len(parts) < 4:
        print("Could not find sections!")
        return

    # parts[0] is imports
    # parts[1] is YouTube
    # parts[2] is Instagram
    # parts[3] is Main

    def prefix_prints(text, prefix):
        # find print("...") or print(f"...") and inject the prefix
        # We need to be careful about newlines like print("\n▶ Starting...")
        # If it starts with \n, put \n[PREFIX], else put [PREFIX]
        
        def replacer(match):
            func = match.group(1) # print(
            quote = match.group(2) # " or f"
            inner = match.group(3)
            
            if inner.startswith('\\n'):
                return f"{func}{quote}\\n[{prefix}] {inner[2:]}"
            elif inner.startswith('\n'):
                return f"{func}{quote}\n[{prefix}] {inner[1:]}"
            else:
                return f"{func}{quote}[{prefix}] {inner}"
                
        # Regex to match print("...") or print(f"...")
        # match group 1: print(
        # match group 2: f" or " or f' or '
        # match group 3: inner content
        # match group 4: closing quote and parenthesis
        pattern = r'(print\()(f?["\'])(.*?)(["\']\))'
        return re.sub(pattern, replacer, text, flags=re.DOTALL)

    parts[1] = prefix_prints(parts[1], 'YT')
    parts[2] = prefix_prints(parts[2], 'IG')
    parts[3] = prefix_prints(parts[3], 'SYS')

    final_content = parts[0] + '# ─────────────────────────────────────────────' + parts[1] + '# ─────────────────────────────────────────────' + parts[2] + '# ─────────────────────────────────────────────' + parts[3]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print("Done tagging prints.")

process_file('c:/Users/ASMIT/Desktop/MyProjects/Reelix/uploader.py')
