# Gmail-Email-Categorization
This program connects securely to a Gmail account using Google OAuth 2.0 authentication and the official Gmail API. After the user grants read-only access, the program retrieves email metadata in batches to avoid API limits and performance issues.

Instead of reading each email individually, the code uses batch processing to efficiently fetch the “From” header of multiple emails at once. The sender email IDs are extracted and counted to determine how many emails were received from each sender.

The final result is a frequency-based categorization of senders (i.e., identifying which email IDs send the most emails). These results are sorted in descending order and stored in a text file for further analysis or reporting. The program includes error handling to safely skip unavailable or restricted emails without stopping execution.
