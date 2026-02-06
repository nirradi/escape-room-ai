# Escape Room - Docker Quick Reference

## Architecture

This is a **self-contained Docker setup**. Everything needed to run the game (Ollama LLM service + Python app) is bundled in a single image.

- No external services required
- Model cache persists in Docker volumes
- Completely reproducible across machines

## Build & Run

### First build (includes model download)
```bash
docker-compose up --build
```

On first run:
1. Docker builds the image (installs Python, Ollama, dependencies)
2. Container starts and launches Ollama service
3. Model (llama3.1:8b ~4-6GB) downloads automatically
4. Game starts and waits for player input

### Subsequent runs (instant)
```bash
docker-compose up
```

Model is cached, so startup is much faster.

## Development

### Live code editing
```bash
docker-compose -f docker-compose.dev.yml up --build
```

This mounts your project code into the container, so changes are reflected immediately without rebuilding.

### Run tests
```bash
docker-compose run game pytest tests/
```

### Run with different level
```bash
docker-compose run game python game/loop.py --evaluator-type llm --narrator-type llm --level bobs-plan.yaml
```

### Run with stub evaluator (no LLM - faster)
```bash
docker-compose run game python game/loop.py --evaluator-type stub --narrator-type llm --level between-floors.yaml
```

### Interactive bash in container
```bash
docker-compose run game bash
```

## Troubleshooting

### Model download is very slow
- The llama3.1:8b model is 4-6GB - this is normal on first run
- Check your internet connection
- Monitor progress: the container logs will show download status

### Out of disk space
```bash
# See Docker disk usage
docker system df

# Delete everything (models, containers, images)
docker-compose down -v
docker system prune -a

# Rebuild (will re-download model)
docker-compose up --build
```

### Clear just the model cache (keep image)
```bash
docker volume rm escape-room_ollama_cache
```

### Build hangs or fails
```bash
# Force rebuild without cache
docker-compose build --no-cache
```

### Permission issues on Mac
- Ensure Docker Desktop is running
- If volume mount issues: `docker system prune -a` and retry

## Environment

Key environment variable inside container:
- `OLLAMA_BASE_URL=http://localhost:11434` - Ollama runs on localhost inside the container

To customize the LLM model or settings, edit `config/models.dev.yaml`.

## Production Considerations

For production deployment:

1. **Image size**: The image includes Ollama (~350MB) + Python dependencies (~500MB)

2. **Resource requirements**: 
   - CPU: 2+ cores recommended
   - Memory: 8GB+ (for llama3.1:8b)
   - Disk: 10GB+ (model + container)

3. **Model options**: Edit the Dockerfile and replace `llama3.1:8b` with:
   - Smaller: `mistral:7b` or `neural-chat:7b` (~4GB)
   - Faster: `phi:latest` or `orca-mini` (~3GB)
   - More capable: `llama2:70b` (~40GB - needs lots of RAM)

4. **Persistent storage**: Models are stored in the `ollama_cache` Docker volume. Keep this volume across deployments to avoid re-downloading.

5. **Logging**: Check logs with:
   ```bash
   docker-compose logs -f game
   ```

## Advanced: Customize the Model

Edit the `Dockerfile` line that says `ollama pull llama3.1:8b` to use a different model, for example:
```bash
ollama pull mistral:7b
```

Then rebuild:
```bash
docker-compose build --no-cache
docker-compose up
```

## Health Checks

The container automatically:
1. Starts Ollama service
2. Waits for Ollama to be ready (max 60s)
3. Pulls the model if not cached
4. Launches the game

If the container exits unexpectedly, check logs: `docker-compose logs`

