# Production Scaling Guide

## 🎯 Current vs. Production Architecture

### Current Setup (Local Dev)
```
┌──────────────────────────────────────────────────┐
│ Single Machine                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│  Files → Pipeline → PostgreSQL                   │
│  (local)  (sync)    (localhost)                  │
│                                                  │
│  Limitations:                                    │
│  • Processes 1 file at a time                    │
│  • No fault tolerance                            │
│  • ~100-1000 files max                           │
│  • Manual triggering                             │
└──────────────────────────────────────────────────┘
```

### Production Setup (Scaled)
```
┌──────────────────────────────────────────────────────────────┐
│ Distributed Cloud Architecture                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  S3 Bucket → Queue → Worker Pool → Postgres (RDS/Supabase)  │
│  (infinite)  (SQS)   (ECS/Lambda)   (managed)                │
│                                                              │
│  Benefits:                                                   │
│  • Process millions of files                                 │
│  • Auto-scaling workers                                      │
│  • Fault tolerant (retries)                                  │
│  • Real-time triggering                                      │
│  • Geographic distribution                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Scaling Stages

### Stage 1: Hundreds of Files/Day
**Keep Current Setup, Optimize**

```bash
# Add more workers (parallel processing)
# Create: run_parallel.py

from multiprocessing import Pool
from src.pipeline.runner import PipelineRunner

def process_file(file_path):
    runner = PipelineRunner()
    runner._process_file(db, file_path)

if __name__ == "__main__":
    files = reader.list_files()

    # Process with 4 workers
    with Pool(4) as pool:
        pool.map(process_file, files)
```

**Estimated Capacity:** 1,000-5,000 files/day

---

### Stage 2: Thousands of Files/Day
**Move to Cloud Database**

#### Option A: Supabase (Easiest)
Free tier → $25/month for production

```bash
# 1. Create Supabase project at supabase.com
# 2. Get connection string
# 3. Update .env

DATABASE_URL=postgresql://postgres:[password]@[project].supabase.co:5432/postgres
```

#### Option B: AWS RDS
More control, ~$50-200/month

```bash
# 1. Create RDS PostgreSQL instance
# 2. Update security groups
# 3. Update .env

DATABASE_URL=postgresql://user:pass@your-rds.amazonaws.com:5432/leadgen_db
```

**Why?**
- Managed backups
- Better performance
- Multiple connections
- Geographic replication

**Estimated Capacity:** 5,000-50,000 files/day

---

### Stage 3: Tens of Thousands of Files/Day
**Add Queue + Multiple Workers**

#### Architecture Change

```
Before: Files → Pipeline → DB (synchronous)
After:  Files → Queue → Workers → DB (async)
```

#### Implementation: Redis Queue

**Install Redis:**
```bash
# docker-compose.yml - add Redis
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**Add Queue Layer:**

Create `src/queue/publisher.py`:
```python
import redis
import json

class JobPublisher:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379)

    def publish_file(self, file_path):
        job = {
            'file_path': file_path,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.redis.lpush('file_queue', json.dumps(job))
```

Create `src/queue/worker.py`:
```python
import redis
import json
from src.pipeline.runner import PipelineRunner

class QueueWorker:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379)
        self.runner = PipelineRunner()

    def run(self):
        while True:
            # Block until job available
            _, job_data = self.redis.brpop('file_queue')
            job = json.loads(job_data)

            try:
                self.runner.process_file(job['file_path'])
                print(f"✓ Processed {job['file_path']}")
            except Exception as e:
                # Put back in queue for retry
                self.redis.lpush('failed_queue', job_data)
                print(f"✗ Failed {job['file_path']}: {e}")
```

**Run Multiple Workers:**
```bash
# Terminal 1
python -m src.queue.worker

# Terminal 2
python -m src.queue.worker

# Terminal 3
python -m src.queue.worker

# Now you have 3 workers processing in parallel!
```

**Estimated Capacity:** 50,000-500,000 files/day

---

### Stage 4: Production Scale (Cloud)
**Full AWS/GCP Architecture**

#### Components

1. **S3 for File Storage**
   - Infinite scale
   - Event triggers
   - Versioning

2. **SQS/SNS for Queue**
   - Managed service
   - Auto-scaling
   - Dead-letter queues

3. **ECS/Fargate for Workers**
   - Docker containers
   - Auto-scale based on queue depth
   - Pay per use

4. **RDS/Aurora for Database**
   - Read replicas
   - Auto-failover
   - Performance Insights

#### Migration Steps

**Step 1: Move Files to S3**

Update `src/io/raw_reader.py`:
```python
import boto3

class RawFileReader:
    def __init__(self, bucket_name: str):
        self.s3 = boto3.client('s3')
        self.bucket = bucket_name

    def list_files(self, prefix=""):
        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix
        )
        return [obj['Key'] for obj in response.get('Contents', [])]

    def read_file(self, s3_key: str):
        response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
        content = response['Body'].read().decode('utf-8')

        # Determine type from extension
        file_type = s3_key.split('.')[-1]
        return content, file_type
```

**Step 2: S3 Event Trigger**

```python
# AWS Lambda function triggered by S3 upload
import boto3
import json

sqs = boto3.client('sqs')
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/your-queue'

def lambda_handler(event, context):
    for record in event['Records']:
        s3_key = record['s3']['object']['key']

        # Send to SQS
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({
                'bucket': record['s3']['bucket']['name'],
                's3_key': s3_key
            })
        )
```

**Step 3: Dockerize Worker**

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY main.py .

CMD ["python", "-m", "src.queue.worker"]
```

**Step 4: Deploy to ECS**

```bash
# Build and push
docker build -t leadgen-worker .
docker tag leadgen-worker:latest your-ecr-repo/leadgen-worker:latest
docker push your-ecr-repo/leadgen-worker:latest

# ECS auto-scales based on SQS queue depth
```

**Estimated Capacity:** Millions of files/day

---

## 💰 Cost Comparison

### Current Setup (Local)
```
Database:     $0 (local PostgreSQL)
Compute:      $0 (your machine)
Storage:      $0 (local disk)
LLM:          ~$20-200/month (based on volume)
Search:       ~$10-50/month (based on new entities)
──────────────────────────────────
TOTAL:        $30-250/month
```

### Small Production (1K files/day)
```
Database:     $25/month (Supabase)
Compute:      $50/month (small VPS)
Storage:      $5/month (S3)
LLM:          ~$100/month
Search:       ~$20/month
──────────────────────────────────
TOTAL:        $200/month
```

### Medium Production (50K files/day)
```
Database:     $200/month (RDS db.t3.medium)
Compute:      $300/month (ECS - 4 workers)
Storage:      $50/month (S3)
LLM:          ~$2,000/month
Search:       ~$100/month
Queue:        $20/month (SQS)
──────────────────────────────────
TOTAL:        $2,670/month
```

### Large Production (500K files/day)
```
Database:     $1,500/month (Aurora cluster)
Compute:      $2,000/month (ECS - 20 workers)
Storage:      $300/month (S3)
LLM:          ~$15,000/month
Search:       ~$500/month
Queue:        $100/month (SQS)
Monitoring:   $200/month (DataDog)
──────────────────────────────────
TOTAL:        $19,600/month
```

---

## 🔍 Monitoring & Observability

### Add Structured Logging

Update pipeline to log JSON:
```python
import logging
import json

logger = logging.getLogger(__name__)

# Log structured events
logger.info(json.dumps({
    'event': 'file_processed',
    'file_path': file_path,
    'entity_id': entity.id,
    'score': lead.score,
    'duration_ms': duration,
    'timestamp': datetime.utcnow().isoformat()
}))
```

### Metrics to Track

1. **Throughput**
   - Files processed per hour
   - Events extracted per hour
   - Entities created per hour

2. **Quality**
   - Extraction confidence average
   - Enrichment success rate
   - Entity resolution match rate

3. **Performance**
   - Processing time per file
   - LLM call duration
   - Database query time

4. **Errors**
   - Failed extractions
   - Failed enrichments
   - Queue retries

### Production Monitoring Stack

```bash
# docker-compose.yml additions

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

---

## 🛡️ Security Considerations

### API Keys
```bash
# Use AWS Secrets Manager or similar
import boto3

secrets = boto3.client('secretsmanager')
response = secrets.get_secret_value(SecretId='leadgen/openai-key')
OPENAI_API_KEY = json.loads(response['SecretString'])['api_key']
```

### Database
```bash
# Use SSL connections
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Rotate credentials regularly
# Use IAM authentication for RDS
```

### Network
```bash
# Use VPC for workers
# Only expose API endpoints publicly
# Use API Gateway with authentication
```

---

## 📈 Recommended Migration Path

### Month 1: Validate
- Run locally with real data
- Tune scoring rules for your domain
- Monitor LLM costs
- **Goal:** Validate value before scaling

### Month 2: Cloud Database
- Move to Supabase/RDS
- Keep processing local
- Add monitoring
- **Goal:** Separate compute from storage

### Month 3: Add Queue
- Add Redis queue
- Run 2-3 workers
- Implement retries
- **Goal:** Async processing

### Month 4: Cloud Migration
- Move to S3
- Dockerize workers
- Deploy to ECS/Lambda
- **Goal:** Auto-scaling production

---

## 🚨 Common Pitfalls

1. **LLM Rate Limits**
   - Add exponential backoff
   - Cache results
   - Batch requests

2. **Database Connections**
   - Use connection pooling
   - Close connections properly
   - Monitor connection count

3. **Memory Leaks**
   - Process files in batches
   - Clear caches periodically
   - Monitor worker memory

4. **Cost Overruns**
   - Set LLM budget limits
   - Monitor daily costs
   - Use cheaper models for retries

---

## 🎓 Next Steps

1. **Run with your data** (use QUICKSTART.md)
2. **Tune for your domain** (adjust scoring, event types)
3. **Monitor costs** (start small, measure)
4. **Scale gradually** (follow migration path above)

Questions? Check the main README.md or open an issue on GitHub.
