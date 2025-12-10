# Anatomie Prompt Generator

A FastAPI service that generates intelligent fashion image prompts for ANATOMIE's luxury performance travel wear brand. The system combines Airtable data with optional LLM-powered structure selection and ML-driven preference learning to create production-ready fashion photography descriptions.

## Features

- **Intelligent Prompt Generation**: Selects designers, colors, garments, and prompt structures based on performance metrics
- **ML-Powered Preference Learning**: Learns from successful images to bias future prompts toward winning attributes
- **Structure Optimization**: Uses optimizer-trained scores to select high-performing prompt structures
- **Exploration vs Exploitation**: Balances consistency (80%) with creative novelty (20%) for continuous improvement
- **Dual Mode Operation**: Works with or without OpenAI API integration
- **Airtable Integration**: Fetches real-time data from Anatomie's design database
- **RESTful API**: Simple HTTP endpoints for generation and preference management

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

### Update preferences (typically called by Orchestrator)

```bash
curl -X POST http://localhost:8000/update_preferences \
  -H "Content-Type: application/json" \
  -d '{
    "global_preference_vector": {
      "earth_tones": 0.82,
      "minimalist": 0.75,
      "clean_finish": 0.79
    },
    "exploration_rate": 0.2,
    "structure_scores": {
      "recStruct1": 0.87,
      "recStruct2": 0.72
    },
    "structure_prompt_insights": {
      "recStruct1": {
        "top_prompts": [
          {"prompt_preview": "flowing silhouette...", "success_rate": 0.85}
        ],
        "avg_success_rate": 0.72
      }
    }
  }'
```

### Check preference status

```bash
curl http://localhost:8000/preferences
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
- **LLM Agent** (`app/llm_agent.py`): Intelligent prompt generation with preference-guided selection
- **Preference Adapter** (`app/preferences.py`): Manages learned preferences, structure scores, and prompt insights
- **Configuration** (`app/config.py`): Centralized settings management
- **Models** (`app/models.py`): Pydantic data models for request/response validation

### Prompt Selection Algorithm

The system uses an intelligent strategy combining ML optimization with exploration:

1. **Exploitation Mode** (80% of time, when preferences loaded):
   - Uses optimizer-trained structure scores for weighted selection
   - Injects learned attribute preferences into LLM context
   - References high-performing prompt examples for each structure
   - Fallback: Uses heuristic scoring (outlier count, ratings, z-scores, recency)

2. **Exploration Mode** (20% of time):
   - Favors newer structures (age < 4 weeks) for creative diversity
   - Tests less-used structures to discover new winning patterns
   - Encourages LLM to experiment with novel combinations

3. **Garment Distribution**:
   - 75% tops (shirts, polos, sweaters)
   - 25% others (dresses, outerwear, pants)

### Preference Learning System

The Generator learns from the Optimizer's ML models:

- **Global Preference Vector**: Attribute scores (e.g., "earth_tones": 0.82) guide prompt style
- **Structure Scores**: ML-predicted success probability per prompt structure
- **Prompt Insights**: Top-performing prompt examples per structure for LLM inspiration
- **Graceful Degradation**: Works without preferences, uses heuristic scoring as fallback

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
- `OPTIMIZER_SERVICE_URL` (default: https://optimizer-2ym2.onrender.com)
- `PREFERENCE_EXPLORATION_RATE` (default: 0.2 = 20% exploration)

## Development

### Project Structure

```
anatomie-prompt-generator/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   ├── models.py            # Pydantic models
│   ├── preferences.py       # ML preference learning
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

## API Endpoints

### Core Endpoints

- `GET /` - Service info
- `GET /health` - Health check with preference status
- `POST /generate-prompts` - Generate fashion image prompts

### Preference Management Endpoints (v1.1.0+)

- `POST /update_preferences` - Update preferences from Optimizer (called by Orchestrator)
- `GET /preferences` - View current preference status
- `GET /preferences/structure/{structure_id}` - Get insights for specific structure
- `GET /preferences/structures/top` - List top-performing structures
- `GET /preferences/exploration_stats` - View exploration vs exploitation statistics
- `POST /preferences/reset_exploration_stats` - Reset tracking counters
- `DELETE /preferences` - Clear all preferences

### Local Development Mode

The application automatically operates in local mode when `OPENAI_API_KEY` is not set, using deterministic prompt generation without requiring external API calls.

## License

Copyright © 2024 Anatomie. All rights reserved.

## Support

For issues or questions, please check the Render logs or contact the development team.
