"""File-level corruption patterns (delimiters, BOM, encoding)."""
import random
import csv
import io

class CorruptionEngine:
    """Apply file-level corruptions."""
    
    @staticmethod
    def apply_delimiter_chaos(content, delimiter=','):
        """Randomly change delimiter in some lines."""
        lines = content.splitlines()
        new_lines = []
        for i, line in enumerate(lines):
            if i > 0 and random.random() < 0.03:  # 3% of data lines
                # Change delimiter to pipe or tab
                new_delim = random.choice(['|', '\t'])
                new_line = line.replace(delimiter, new_delim)
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        return '\n'.join(new_lines)
    
    @staticmethod
    def add_bom(content):
        """Add UTF-8 BOM marker to beginning."""
        return '\ufeff' + content
    
    @staticmethod
    def inject_excel_formulas(content):
        """Wrap some numeric fields in Excel formula syntax."""
        lines = content.splitlines()
        new_lines = [lines[0]]  # header unchanged
        for line in lines[1:]:
            if random.random() < 0.05:
                # Wrap first numeric-looking field in ="..."
                parts = line.split(',')
                for i, part in enumerate(parts):
                    if part.replace('.', '').isdigit():
                        parts[i] = f'="{part}"'
                        break
                line = ','.join(parts)
            new_lines.append(line)
        return '\n'.join(new_lines)
    
    @staticmethod
    def truncate_file(content, max_rows=5000):
        """Truncate to max_rows for stress testing partial exports."""
        lines = content.splitlines()
        if len(lines) > max_rows:
            return '\n'.join(lines[:max_rows])
        return content
    
    @staticmethod
    def random_encoding_mangle(content):
        """Corrupt random characters to simulate encoding mismatch."""
        chars = list(content)
        for i in range(len(chars)):
            if random.random() < 0.001:  # 0.1% corruption
                chars[i] = random.choice(['�', 'Ã©', 'â€', 'Â'])
        return ''.join(chars)