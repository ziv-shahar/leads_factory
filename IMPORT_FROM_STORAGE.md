# Import Files from Supabase Storage

This guide shows you how to import files from another Supabase project's Storage into your local pipeline for processing.

## Quick Start

### Method 1: Using Environment File (Recommended)

1. **Copy the example environment file:**
   ```bash
   cp .env.storage.example .env.storage
   ```

2. **Edit `.env.storage` with your Supabase Storage credentials:**
   ```bash
   nano .env.storage
   ```

   Fill in:
   ```env
   SOURCE_SUPABASE_URL=https://xxxxx.supabase.co
   SOURCE_SUPABASE_KEY=your-service-role-key-here
   SOURCE_BUCKET_NAME=your-bucket-name
   SOURCE_FOLDER_PATH=optional-folder-path
   ```

3. **Run the import script:**
   ```bash
   python3 import_from_supabase_storage.py
   ```

### Method 2: Using Environment Variables

```bash
export SOURCE_SUPABASE_URL="https://xxxxx.supabase.co"
export SOURCE_SUPABASE_KEY="your-service-role-key"
export SOURCE_BUCKET_NAME="raw-data"
export SOURCE_FOLDER_PATH="leads/2024"

python3 import_from_supabase_storage.py
```

### Method 3: Edit Script Directly

Edit `import_from_supabase_storage.py` and set the values directly in the Configuration section:

```python
SOURCE_SUPABASE_URL = "https://xxxxx.supabase.co"
SOURCE_SUPABASE_KEY = "your-service-role-key"
SOURCE_BUCKET_NAME = "raw-data"
SOURCE_FOLDER_PATH = "leads/2024"
```

## Configuration Details

### SOURCE_SUPABASE_URL
Your source Supabase project URL (the one with the files).

**Where to find it:**
- Go to your Supabase project dashboard
- Settings → API → Project URL
- Example: `https://abcdefghijk.supabase.co`

### SOURCE_SUPABASE_KEY
Authentication key for accessing the storage bucket.

**Where to find it:**
- Go to your Supabase project dashboard
- Settings → API → Project API keys

**Which key to use:**
- **`service_role` key** (recommended): Can access all files, including private buckets
- **`anon` key**: Only works for public buckets

⚠️ **Security Note:** Never commit keys to git! Use `.env.storage` (already in `.gitignore`)

### SOURCE_BUCKET_NAME
Name of the storage bucket containing your files.

**Where to find it:**
- Go to your Supabase project dashboard
- Storage → View all buckets
- Copy the bucket name (e.g., "raw-data", "documents", "leads")

### SOURCE_FOLDER_PATH
(Optional) Specific folder within the bucket to import.

**Examples:**
- `""` or empty: Import all files from bucket root
- `"companies"`: Import only from companies folder
- `"leads/2024/january"`: Import from nested folder

**How folder structure is preserved:**
If your storage has:
```
raw-data/
  ├── companies/
  │   ├── doc_01.json
  │   └── doc_02.json
  └── buildings/
      └── permit.json
```

And you set `SOURCE_FOLDER_PATH="companies"`, it will download to:
```
raw_data_bucket/
  ├── doc_01.json
  └── doc_02.json
```

If you set `SOURCE_FOLDER_PATH=""`, it will download to:
```
raw_data_bucket/
  ├── companies/
  │   ├── doc_01.json
  │   └── doc_02.json
  └── buildings/
      └── permit.json
```

## What the Script Does

1. **Connects** to your source Supabase project
2. **Lists** all files in the specified bucket/folder
3. **Downloads** files to `raw_data_bucket/` (preserves directory structure)
4. **Skips** files that already exist locally
5. **Reports** success, skipped, and failed file counts

## Example Output

```
================================================================================
Import Files from Supabase Storage
================================================================================

🔗 Connecting to source Supabase project...
   URL: https://xxxxx.supabase.co
   Bucket: raw-data
   Folder: companies

📂 Listing files in storage...
   Found 15 files

⬇️  Downloading files to /home/user/leads_factory/raw_data_bucket...

  ✓ Downloaded: companies/doc_01.json → raw_data_bucket/companies/doc_01.json
  ✓ Downloaded: companies/doc_02.json → raw_data_bucket/companies/doc_02.json
  ⊘ Skipped (exists): companies/doc_03.json

================================================================================
Import Complete
================================================================================
  ✓ Successfully downloaded: 13 files
  ⊘ Skipped (already exist): 1 files
  ✗ Failed: 1 files
================================================================================

✓ Files saved to: /home/user/leads_factory/raw_data_bucket

Next steps:
  1. Run the pipeline: python3 main.py run
  2. View results in Supabase database
```

## After Import

Once files are downloaded, process them with your pipeline:

```bash
python3 main.py run
```

This will:
- Extract entities and events from the imported files
- Normalize locations to 2-letter state codes
- Create location-based leads per state
- Store results in your Supabase database

## Troubleshooting

### Error: "Missing configuration"
Make sure you set all required environment variables or created `.env.storage` file.

### Error: "Invalid API key"
- Check that your `SOURCE_SUPABASE_KEY` is correct
- Try using the `service_role` key instead of `anon` key
- Verify the key is from the source project (not destination)

### Error: "Bucket not found"
- Check that `SOURCE_BUCKET_NAME` matches exactly (case-sensitive)
- Verify the bucket exists in your source Supabase project
- Check bucket permissions (may need to be public or use service_role key)

### Error: "Permission denied"
- Use `service_role` key for private buckets
- Or make the bucket public (Storage → Settings → Make bucket public)

### Files not downloading
- Check that files actually exist in the specified folder path
- Try setting `SOURCE_FOLDER_PATH=""` to import entire bucket
- Verify bucket has files (check in Supabase dashboard → Storage)

## Security Best Practices

1. ✅ **DO** use `.env.storage` file (it's in `.gitignore`)
2. ✅ **DO** use `service_role` key for private data
3. ❌ **DON'T** commit API keys to git
4. ❌ **DON'T** share your `service_role` key publicly
5. ❌ **DON'T** hardcode credentials in the script if committing to git

## Advanced Usage

### Import Multiple Folders

Run the script multiple times with different `SOURCE_FOLDER_PATH`:

```bash
# Import companies folder
export SOURCE_FOLDER_PATH="companies"
python3 import_from_supabase_storage.py

# Import buildings folder
export SOURCE_FOLDER_PATH="buildings"
python3 import_from_supabase_storage.py
```

### Schedule Automatic Imports

Add to crontab for daily imports:

```bash
# Run every day at 2 AM
0 2 * * * cd /home/user/leads_factory && python3 import_from_supabase_storage.py >> logs/import.log 2>&1
```

### Import from Multiple Projects

Create separate config files:

```bash
# Project A
cat > .env.storage.projectA << EOF
SOURCE_SUPABASE_URL=https://projecta.supabase.co
SOURCE_SUPABASE_KEY=key-a
SOURCE_BUCKET_NAME=bucket-a
EOF

# Project B
cat > .env.storage.projectB << EOF
SOURCE_SUPABASE_URL=https://projectb.supabase.co
SOURCE_SUPABASE_KEY=key-b
SOURCE_BUCKET_NAME=bucket-b
EOF

# Import from each
python3 import_from_supabase_storage.py  # Uses .env.storage
# Or modify script to accept config file as argument
```
