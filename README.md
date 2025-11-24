# ANATOMIE Prompt Generator

A FastAPI service that generates intelligent fashion image prompts for ANATOMIE's luxury performance travel wear brand. The system combines Airtable data with optional LLM-powered structure selection to create production-ready fashion photography descriptions.

## Features

- **Intelligent Prompt Generation**: Selects designers, colors, garments, and prompt structures based on performance metrics
- **Dual Mode Operation**: Works with or without OpenAI API integration
- **Airtable Integration**: Fetches real-time data from ANATOMIE's design database
- **Performance-Optimized**: Evolving structure selection algorithm prioritizes high-performing templates
- **RESTful API**: Simple HTTP endpoint for easy integration

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/edebbyi/anatomie-prompt-generator.git
   cd anatomie-prompt-generator
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   - `AIRTABLE_API_KEY`: Your Airtable API key
   - `AIRTABLE_BASE_ID`: Your Airtable base ID
   - `OPENAI_API_KEY`: (Optional) OpenAI API key for LLM-enhanced generation

## Usage

### Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

### Generate prompts

```bash
curl -X POST http://localhost:8000/generate-prompts \
  -H "Content-Type: application/json" \
  -d '{
    "num_prompts": 10,
    "renderer": "ImageFX"
  }'
```

### Response format

```json
{
  "prompts": [
    {
      "promptText": "16K ultra-high resolution fashion photography...",
      "designerId": "recXXXXXXXXXXXXXX",
      "garmentId": "recYYYYYYYYYYYYYY",
      "promptStructureId": "recZZZZZZZZZZZZZZ",
      "renderer": "ImageFX"
    }
  ]
}
```

## Architecture

### Components

- **API Layer** (`app/main.py`): FastAPI application handling HTTP requests
- **Airtable Client** (`app/airtable_client.py`): Fetches designers, colors, garments, and prompt structures
- **LLM Agent** (`app/llm_agent.py`): Intelligent prompt generation with evolving structure selection
- **Configuration** (`app/config.py`): Centralized settings management
- **Models** (`app/models.py`): Pydantic data models for request/response validation

### Prompt Selection Algorithm

The system uses an evolving strategy to select prompt structures:

1. **Performance-Based Selection** (80-85% of time):
   - Prioritizes structures with high outlier counts
   - Considers average ratings (>3.5)
   - Factors in recency (age < 12 weeks)
   - Weighs positive z-scores

2. **Exploratory Selection** (15-20% of time):
   - Tests newer structures (age < 4 weeks)
   - Evaluates less-used structures with positive AI critiques

3. **Garment Distribution**:
   - 75% tops (shirts, polos, sweaters)
   - 25% others (dresses, outerwear, pants)

## Testing

Run the test suite:

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_llm_agent.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## Deployment

### Render.com

The application is configured for deployment on Render.com via `render.yaml`:

1. Push changes to GitHub
2. Render automatically deploys from the main branch
3. Configure environment variables in Render dashboard
4. Update `SERVICE_URL` in Airtable automation script if needed

### Environment Variables

Required:
- `AIRTABLE_API_KEY`
- `AIRTABLE_BASE_ID`
- All table and view IDs (see `.env` file)

Optional:
- `OPENAI_API_KEY` (enables LLM-enhanced generation)
- `OPENAI_MODEL` (default: gpt-4o-mini)
- `OPENAI_TEMPERATURE` (default: 0.4)

## Development

### Project Structure

```
anatomie-prompt-generator/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   ├── models.py            # Pydantic models
│   ├── airtable_client.py   # Airtable integration
│   └── llm_agent.py         # Prompt generation logic
├── tests/
│   ├── test_api.py
│   ├── test_airtable_client.py
│   └── test_llm_agent.py
├── requirements.txt
├── render.yaml
└── .env
```

### Local Development Mode

The application automatically operates in local mode when `OPENAI_API_KEY` is not set, using deterministic prompt generation without requiring external API calls.

## License

Copyright © 2024 ANATOMIE. All rights reserved.

## Support

For issues or questions, please check the Render logs or contact the development team.
