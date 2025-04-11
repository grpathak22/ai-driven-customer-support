# Support Issue Analyzer

A Streamlit application that analyzes support issues, finds similar historical cases, assigns teams, and estimates resolution times using a combination of vector similarity search and LLM-assisted classification.

## Features

- **Issue Analysis**: Analyze support issues and find similar historical cases
- **Team Assignment**: Automatically assign issues to the appropriate team
- **Resolution Time Estimation**: Estimate resolution time based on historical data
- **LLM Integration**: Fall back to LLM recommendations when no similar historical cases are found
- **Conversation History**: Maintain conversation context between interactions
- **Data Upload**: Upload custom historical ticket data

## Directory Structure

```
app/
├── __init__.py       - Package initialization file
├── app.py            - Main Streamlit app UI
├── main.py           - Entry point for running the app
├── get_response.py   - OpenAI client for LLM interactions
├── chroma_agent.py   - ChromaDB agent for vector similarity search
└── assign_agent.py   - Team assignment and resolution time estimation
```

## Setup and Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the Streamlit app:
   ```
   streamlit run app/main.py
   ```

## Usage

1. Load historical ticket data (use the sample data or upload your own CSV)
2. Enter a support issue description in the text area
3. Adjust the number of similar issues to find if needed
4. Click "Analyze Issue" to process the request
5. View the results, including team assignment, resolution time, and similar issues
6. Continue the conversation to refine the issue or analyze new ones

## Data Format

The app expects CSV files with the following columns:
- `Ticket_ID`: Unique identifier for each ticket
- `Issue_Category`: The category or description of the issue
- `Solution`: The solution applied to the issue
- `Ticket_Open_Date`: The date and time when the ticket was opened
- `Date_of_Resolution`: The date and time when the ticket was resolved
- `Assigned_To_Team`: The team that resolved the issue

## Technical Details

- Uses [Streamlit](https://streamlit.io/) for the web UI
- Uses [ChromaDB](https://www.trychroma.com/) for vector similarity search
- Uses [SentenceTransformers](https://www.sbert.net/) for embedding generation
- Uses [OpenAI API](https://platform.openai.com/) for LLM integration
- Maintains conversation context for improved responses
- Applies weighted voting for team assignment
- Calculates weighted average for resolution time estimation 