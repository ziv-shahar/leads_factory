# Architecture Overview

## Current State (What You Have Now)

### Data Flow
```
┌─────────────────────────────────────────────────────────────────────┐
│ YOUR LOCAL DEVELOPMENT MACHINE                                      │
│                                                                     │
│  ┌────────────────┐                                                │
│  │ raw_data_bucket│ ← You put files here manually                  │
│  │  - doc_01.html │                                                │
│  │  - doc_02.json │                                                │
│  │  - doc_03.txt  │                                                │
│  └────────┬───────┘                                                │
│           │                                                         │
│           │ python main.py run                                     │
│           ↓                                                         │
│  ┌────────────────────────────────────────────────────┐            │
│  │ Pipeline (src/pipeline/runner.py)                  │            │
│  │                                                    │            │
│  │  1. Read file                                     │            │
│  │  2. LLM Extract → NormalizedEvent                 │            │
│  │  3. Web Search → Enrichment (if needed)           │            │
│  │  4. Entity Resolution → Dedupe                    │            │
│  │  5. Score → Lead                                  │            │
│  └────────────────────┬───────────────────────────────┘            │
│                       │                                             │
│                       │ INSERT/UPDATE                               │
│                       ↓                                             │
│  ┌────────────────────────────────────────────┐                    │
│  │ PostgreSQL (localhost:5432)                │                    │
│  │                                            │                    │
│  │  Tables:                                   │                    │
│  │  • raw_events (3 rows)                     │                    │
│  │  • entities (1 row - "ACME CLOUD")         │                    │
│  │  • events (3 rows)                         │                    │
│  │  • leads_current (1 row - score: 137)      │                    │
│  │  • lead_state_history (3 rows)             │                    │
│  └────────────────────────────────────────────┘                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Processing: SYNCHRONOUS (one file at a time)
Capacity:   ~100-1,000 files/day
```

### Storage Breakdown

**File Storage (Filesystem)**
```
/home/user/leads_factory/raw_data_bucket/
├── doc_01.html          1.4 KB
├── doc_02.json          2.3 KB
└── doc_03.txt           2.9 KB
                         -------
                         6.6 KB total
```

**Database Storage (PostgreSQL)**
```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('leadgen_db'));
-- Currently: ~8 MB (mostly empty)

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public';

Results:
├── raw_events         : 16 KB
├── entities           : 16 KB
├── events             : 24 KB (has JSONB)
├── leads_current      : 16 KB
└── lead_state_history : 16 KB
```

---

## Production State (Future)

### Small Production (1K-10K files/day)

```
┌─────────────────────────────────────────────────────────────────┐
│ AWS/GCP CLOUD                                                   │
│                                                                 │
│  ┌─────────────┐                                               │
│  │ S3 Bucket   │ ← Files uploaded via API/webhook/scraper      │
│  │ (infinite)  │                                               │
│  └──────┬──────┘                                               │
│         │                                                       │
│         │ Event trigger on new file                            │
│         ↓                                                       │
│  ┌─────────────┐                                               │
│  │ SQS Queue   │ ← Message queue (async)                       │
│  └──────┬──────┘                                               │
│         │                                                       │
│         │ Workers poll queue                                   │
│         ↓                                                       │
│  ┌────────────────────────────────────┐                        │
│  │ Worker Pool (ECS/Fargate)          │                        │
│  │                                    │                        │
│  │  ┌─────────┐  ┌─────────┐         │                        │
│  │  │Worker #1│  │Worker #2│  ...    │                        │
│  │  └────┬────┘  └────┬────┘         │                        │
│  │       └────────────┬──────────────┘│                        │
│  │                    │                                        │
│  └────────────────────┼────────────────┘                       │
│                       │                                         │
│                       │ Write results                           │
│                       ↓                                         │
│  ┌────────────────────────────────────┐                        │
│  │ RDS PostgreSQL (managed)           │                        │
│  │  - Auto-scaling storage            │                        │
│  │  - Automated backups               │                        │
│  │  - Read replicas                   │                        │
│  └────────────────────────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Processing: ASYNCHRONOUS (parallel workers)
Capacity:   10,000-100,000 files/day
Cost:       ~$200-1,000/month
```

### Large Production (100K+ files/day)

```
┌────────────────────────────────────────────────────────────────────┐
│ DISTRIBUTED CLOUD ARCHITECTURE                                     │
│                                                                    │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                  │
│  │ S3 Bucket│     │ S3 Bucket│     │ S3 Bucket│                  │
│  │ US-East  │     │ EU-West  │     │ AP-South │                  │
│  └────┬─────┘     └────┬─────┘     └────┬─────┘                  │
│       │                │                │                         │
│       └────────────────┼────────────────┘                         │
│                        │                                          │
│                        ↓                                          │
│  ┌────────────────────────────────────────┐                      │
│  │ SNS Topic (fanout)                     │                      │
│  └───────────┬──────────────┬─────────────┘                      │
│              │              │                                     │
│              ↓              ↓                                     │
│  ┌───────────────┐  ┌───────────────┐                           │
│  │ SQS: Extract  │  │ SQS: Enrich   │                           │
│  └───────┬───────┘  └───────┬───────┘                           │
│          │                   │                                    │
│          ↓                   ↓                                    │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │ 20 Workers   │    │ 10 Workers   │                           │
│  │ (Extract)    │    │ (Enrich)     │                           │
│  └──────┬───────┘    └──────┬───────┘                           │
│         │                   │                                    │
│         └───────────┬───────┘                                    │
│                     │                                            │
│                     ↓                                            │
│  ┌────────────────────────────────────────┐                     │
│  │ Aurora PostgreSQL Cluster              │                     │
│  │  - Writer instance                     │                     │
│  │  - 2 Read replicas (for API queries)   │                     │
│  │  - Auto-failover                       │                     │
│  └────────────────────────────────────────┘                     │
│                     │                                            │
│                     ↓                                            │
│  ┌────────────────────────────────────────┐                     │
│  │ API Layer (FastAPI on ECS)             │                     │
│  │  - GET /leads?min_score=50             │                     │
│  │  - GET /entities/{id}                  │                     │
│  │  - GET /events/{id}                    │                     │
│  └────────────────────────────────────────┘                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

Processing: DISTRIBUTED (30+ workers across regions)
Capacity:   1M+ files/day
Cost:       ~$5,000-20,000/month
```

---

## Component Deep Dive

### 1. File Storage Evolution

**Current: Filesystem**
```python
# Simple, local
files = os.listdir('raw_data_bucket/')
```

**Production: S3**
```python
# Infinite scale, versioned, event-driven
import boto3
s3 = boto3.client('s3')
files = s3.list_objects_v2(Bucket='leadgen-files')
```

**Why S3?**
- ✅ Unlimited storage
- ✅ 99.999999999% durability
- ✅ Event triggers (auto-process on upload)
- ✅ Versioning (track changes)
- ✅ Lifecycle policies (auto-delete old files)

---

### 2. Queue Evolution

**Current: None (synchronous)**
```python
for file in files:
    process_file(file)  # Blocks until done
```

**Production: SQS/Redis**
```python
# Publisher
queue.put({'file': 's3://bucket/file.json'})

# Workers (multiple processes)
while True:
    job = queue.get()  # Non-blocking
    process_file(job['file'])
```

**Why Queue?**
- ✅ Decouples ingestion from processing
- ✅ Handles traffic spikes (queue buffers)
- ✅ Retry failed jobs
- ✅ Dead-letter queue for persistent failures
- ✅ Multiple workers process in parallel

---

### 3. Database Evolution

**Current: Local PostgreSQL**
```
Capacity:  ~10K entities, ~100K events
Backup:    Manual
Failover:  None
Cost:      $0
```

**Small Production: Supabase**
```
Capacity:  ~100K entities, ~1M events
Backup:    Automatic (daily)
Failover:  Automatic
Cost:      $25/month
```

**Large Production: AWS Aurora**
```
Capacity:  Millions of entities/events
Backup:    Continuous (point-in-time recovery)
Failover:  <30 seconds automatic
Replicas:  Read replicas for queries
Cost:      $500-2,000/month
```

---

### 4. Worker Scaling

**Current: Single Process**
```
1 machine × 1 process = 1 file at a time
```

**Multi-Process (same machine)**
```python
from multiprocessing import Pool

# 4 cores = 4x throughput
with Pool(4) as pool:
    pool.map(process_file, files)
```

**Auto-Scaling (cloud)**
```yaml
# ECS Task Definition
scaling:
  min_workers: 2
  max_workers: 50
  scale_up_when: queue_depth > 100
  scale_down_when: queue_depth < 10
```

---

## Data Retention & Growth

### Storage Projection

**Assumptions:**
- Average file size: 10 KB
- Average events per file: 2
- Event storage (JSONB): ~2 KB each

**Current (3 files):**
```
Files:    3 × 10 KB = 30 KB
Events:   6 × 2 KB  = 12 KB
Total:    ~42 KB
```

**After 1 Month (10K files):**
```
S3:          10,000 × 10 KB  = 100 MB       ($0.023/month)
PostgreSQL:  20,000 events   = 40 MB        (negligible)
Total:       ~140 MB
```

**After 1 Year (3.6M files):**
```
S3:          3.6M × 10 KB    = 36 GB        ($8.28/month)
PostgreSQL:  7.2M events     = 14 GB        ($15/month for storage)
Total:       ~50 GB
```

---

## Migration Checklist

### Phase 1: Prepare (Week 1)
- [ ] Run locally with real data
- [ ] Tune scoring for your domain
- [ ] Document custom event types
- [ ] Set up cost monitoring

### Phase 2: Cloud Database (Week 2)
- [ ] Create Supabase account
- [ ] Migrate schema with `init_db()`
- [ ] Update DATABASE_URL
- [ ] Verify connection
- [ ] Set up automated backups

### Phase 3: Cloud Storage (Week 3)
- [ ] Create S3 bucket
- [ ] Update `raw_reader.py` for S3
- [ ] Upload test files
- [ ] Verify pipeline works with S3

### Phase 4: Queue System (Week 4)
- [ ] Add Redis/SQS
- [ ] Create publisher script
- [ ] Create worker script
- [ ] Test with 2-3 workers
- [ ] Monitor queue depth

### Phase 5: Production Deploy (Week 5-6)
- [ ] Dockerize application
- [ ] Push to ECR/GCR
- [ ] Deploy to ECS/Cloud Run
- [ ] Configure auto-scaling
- [ ] Set up monitoring (CloudWatch/Datadog)
- [ ] Load test with 1000 files

### Phase 6: Optimize (Ongoing)
- [ ] Add caching (Redis)
- [ ] Optimize database queries
- [ ] Tune LLM prompts for cost
- [ ] Add retry logic
- [ ] Implement circuit breakers

---

## FAQ

### Where is my data stored RIGHT NOW?
**Files:** `/home/user/leads_factory/raw_data_bucket/`
**Database:** PostgreSQL on `localhost:5432`
Both are on your local machine.

### What happens if I restart my machine?
**Files:** Still there (filesystem)
**Database:** Still there (PostgreSQL persists data)
**Pipeline:** You need to run `python main.py run` again

### How do I back up my data?
```bash
# Backup database
pg_dump -U leadgen_user leadgen_db > backup.sql

# Backup files
tar -czf files_backup.tar.gz raw_data_bucket/

# Restore database
psql -U leadgen_user leadgen_db < backup.sql
```

### Can I run this on a server instead of my laptop?
Yes! Just:
1. Install PostgreSQL on the server
2. Run `python main.py init`
3. Add files to `raw_data_bucket/`
4. Run `python main.py run`

### How many files can I process locally?
**Realistic limits:**
- 1,000 files: Easy
- 10,000 files: Possible (takes hours)
- 100,000 files: Need cloud migration

### When should I move to cloud?
**Move when:**
- Processing >1,000 files/day
- Need automated triggering
- Need high availability
- Multiple people using the data
- Files come from external sources

---

## Summary

**You have now:** A fully functional local pipeline
**Next step:** Add your own data (see QUICKSTART.md)
**Later:** Scale to cloud (see PRODUCTION_GUIDE.md)

The beauty of this architecture: **It's the same code**, just different infrastructure!
