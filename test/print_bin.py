import sys
# Path to your binary file
file_path = sys.argv[1]
print(file_path)

# Open the file in binary mode
with open(file_path, 'rb') as file:
    # Read the entire file content into a bytes object
    file_content = file.read()

# Convert each byte in the file content to a formatted string
formatted_output = ''.join(f'\\x{byte:02x}' for byte in file_content)

print(formatted_output)
