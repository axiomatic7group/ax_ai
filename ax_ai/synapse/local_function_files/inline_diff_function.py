import difflib
import re, sys
from django.utils.html import escape

def generate_inline_diff(old_str, new_str):
    """
    Compares two strings and returns safe HTML showing deletions (<del>) and insertions (<ins>),
    while safely preserving original whitespace and line breaks.
    """
    # 1. Handle None or empty values gracefully
    old_str = old_str or ""
    new_str = new_str or ""

    # 2. Escape inputs to prevent XSS attacks before we wrap them in HTML tags
    old_str = escape(old_str)
    new_str = escape(new_str)

    # 3. Use regex split to keep spaces and newlines (\n) as separate tokens
    #    This ensures your large text block keeps its formatting!
    old_words = re.split(r'(\s+)', old_str)
    new_words = re.split(r'(\s+)', new_str)
    
    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    output = []
    
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == 'equal':
            output.append("".join(old_words[i1:i2]))
        elif opcode == 'replace':
            deletion = f"<del class='diff-del'>{''.join(old_words[i1:i2])}</del>"
            insertion = f"<ins class='diff-ins'>{''.join(new_words[j1:j2])}</ins>"
            output.append(f"{deletion}{insertion}")
        elif opcode == 'delete':
            output.append(f"<del class='diff-del'>{''.join(old_words[i1:i2])}</del>")
        elif opcode == 'insert':
            output.append(f"<ins class='diff-ins'>{''.join(new_words[j1:j2])}</ins>")
            
    # 4. Join without spaces (since the regex kept the original spaces)
    html_result = "".join(output)
    
    return print(html_result)


#new_str = "Jolla Corporate Vice President and Chief Accounting Officer (Principal Accounting Officer) Pursuant to the requirements of the Securities Exchange Act of 1934, this report has been signed below by the following persons on behalf of Registrant and in the capacities indicated on July 29, 2026. Signature Title /s/ S ATYA N ADELLA Chairman and Chief Executive Officer (Principal Executive Officer) Satya Nadella /s/ C ARMINE D I S IBIO Director Carmine Di Sibio /s/ R EID G. H OFFMAN Director Reid G. Hoffman /s/ H UGH F. J OHNSTON Director Hugh F. Johnston /s/ T ERI L."
#old_str = "Jolla Corporate Vice President and Chief Accounting Officer (Principal Accounting Officer) Pursuant to the requirements of the Securities Exchange Act of 1934, this report has been signed below by the following persons on behalf of Registrant and in the capacities indicated on July 30, 2025. Signature Title /s/ S ATYA N ADELLA Chairman and Chief Executive Officer (Principal Executive Officer) Satya Nadella /s/ R EID G. H OFFMAN Director Reid G. Hoffman /s/ H UGH F. J OHNSTON Director Hugh F. Johnston /s/ T ERI L."

if __name__ == "__main__":
    if len(sys.argv) == 2:
        print({"error": "Missing function name or URL arguments"})
        sys.exit(1)

    old_str = sys.argv[0]
    new_str = sys.argv[1]

    generate_inline_diff(old_str, new_str)

