"""
Supabase client wrapper that mimics SQLAlchemy interface.

This wrapper provides a SQLAlchemy-like interface for Supabase REST API,
allowing minimal code changes when switching from PostgreSQL to Supabase client.
"""
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import uuid
from supabase import create_client, Client

from src.config import SUPABASE_URL, SUPABASE_KEY
from src.db.models import Base, Entity, Event, RawEvent, LeadCurrent, LeadStateHistory, LocationLead


# Table name mapping
TABLE_MAP = {
    'Entity': 'entities',
    'Event': 'events',
    'RawEvent': 'raw_events',
    'LeadCurrent': 'leads_current',
    'LeadStateHistory': 'lead_state_history',
    'LocationLead': 'location_leads'
}


class SupabaseQuery:
    """Mimics SQLAlchemy Query interface for Supabase."""

    def __init__(self, model_class: Type[Base], supabase: Client):
        self.model_class = model_class
        self.supabase = supabase
        self.table_name = TABLE_MAP[model_class.__name__]
        self._filters = []
        self._limit_value = None

    def filter(self, *conditions):
        """Add filter conditions."""
        for condition in conditions:
            self._filters.append(condition)
        return self

    def first(self) -> Optional[Any]:
        """Get first matching record."""
        query = self.supabase.table(self.table_name).select("*")

        # Apply filters
        for filter_expr in self._filters:
            query = self._apply_filter(query, filter_expr)

        # Limit to 1
        query = query.limit(1)

        result = query.execute()

        if result.data and len(result.data) > 0:
            return self._dict_to_model(result.data[0])
        return None

    def all(self) -> List[Any]:
        """Get all matching records."""
        query = self.supabase.table(self.table_name).select("*")

        # Apply filters
        for filter_expr in self._filters:
            query = self._apply_filter(query, filter_expr)

        if self._limit_value:
            query = query.limit(self._limit_value)

        result = query.execute()

        return [self._dict_to_model(row) for row in result.data]

    def count(self) -> int:
        """Count matching records."""
        query = self.supabase.table(self.table_name).select("id", count="exact")

        # Apply filters
        for filter_expr in self._filters:
            query = self._apply_filter(query, filter_expr)

        result = query.execute()
        return result.count if result.count is not None else 0

    def limit(self, value: int):
        """Limit results."""
        self._limit_value = value
        return self

    def _apply_filter(self, query, filter_expr):
        """Apply a filter expression to the query."""
        # Parse SQLAlchemy-style filter expression
        # e.g., Entity.domain == "example.com"
        # This is simplified - handles basic equality comparisons

        if hasattr(filter_expr, 'left') and hasattr(filter_expr, 'right'):
            # Binary expression (==, !=, etc.)
            column_name = str(filter_expr.left.key)
            operator = filter_expr.operator.__name__
            value = filter_expr.right.value

            if operator == 'eq':
                query = query.eq(column_name, value)
            elif operator == 'ne':
                query = query.neq(column_name, value)
            elif operator == 'gt':
                query = query.gt(column_name, value)
            elif operator == 'lt':
                query = query.lt(column_name, value)
            elif operator == 'like_op':
                # Convert SQL LIKE to Supabase pattern
                query = query.like(column_name, value)

        return query

    def _dict_to_model(self, data: Dict) -> Any:
        """Convert dictionary to model instance."""
        # Create a properly initialized instance
        # SQLAlchemy models need their __init__ called to set up instrumentation
        instance = self.model_class()

        # Set attributes from data
        for key, value in data.items():
            # Convert ISO datetime strings to datetime objects
            if isinstance(value, str) and ('_at' in key or '_time' in key):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass

            # Only set attribute if the model has this column
            if hasattr(instance, key):
                setattr(instance, key, value)

        return instance


class SupabaseSession:
    """Mimics SQLAlchemy Session interface for Supabase."""

    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self._pending_adds = []
        self._committed = False

    def query(self, model_class: Type[Base]) -> SupabaseQuery:
        """Create a query for the given model."""
        return SupabaseQuery(model_class, self.supabase)

    def add(self, instance: Any):
        """Add an instance to be inserted."""
        self._pending_adds.append(instance)

    def flush(self):
        """Flush pending adds to database and update IDs."""
        for instance in self._pending_adds:
            self._insert_instance(instance)
        self._pending_adds.clear()

    def commit(self):
        """Commit transaction (flush any pending adds)."""
        self.flush()
        self._committed = True

    def rollback(self):
        """Rollback transaction."""
        self._pending_adds.clear()
        self._committed = False

    def close(self):
        """Close session."""
        if not self._committed and self._pending_adds:
            # Auto-commit if there are pending adds
            self.commit()

    def _insert_instance(self, instance: Any):
        """Insert a single instance into Supabase."""
        from postgrest.exceptions import APIError

        table_name = TABLE_MAP[instance.__class__.__name__]
        data = self._model_to_dict(instance)

        try:
            # Insert and get the result
            result = self.supabase.table(table_name).insert(data).execute()

            if result.data and len(result.data) > 0:
                # Update instance with returned ID
                returned_row = result.data[0]
                if 'id' in returned_row:
                    instance.id = returned_row['id']

                # Update any other auto-generated fields
                for key, value in returned_row.items():
                    if not hasattr(instance, key) or getattr(instance, key) is None:
                        setattr(instance, key, value)

        except APIError as e:
            # Handle duplicate key constraint violations for LeadCurrent and LocationLead
            # This happens in parallel processing when two threads try to create the same lead

            # APIError.args[0] can be either a dict or a string, handle both
            error_dict = {}
            if e.args:
                if isinstance(e.args[0], dict):
                    error_dict = e.args[0]
                elif isinstance(e.args[0], str):
                    # Sometimes it's a string, try to parse it
                    try:
                        import json
                        error_dict = json.loads(e.args[0])
                    except:
                        # If parsing fails, check the string content
                        error_str = str(e)
                        if '23505' in error_str:
                            error_dict = {'code': '23505'}

            error_code = error_dict.get('code') if isinstance(error_dict, dict) else None

            if error_code == '23505':  # Duplicate key violation
                # Only handle for LeadCurrent and LocationLead (they have unique constraints on entity_id)
                if instance.__class__.__name__ == 'LeadCurrent':
                    # Update existing LeadCurrent instead
                    result = self.supabase.table(table_name).update(data).eq('entity_id', instance.entity_id).execute()
                    if result.data and len(result.data) > 0:
                        returned_row = result.data[0]
                        if 'id' in returned_row:
                            instance.id = returned_row['id']
                        for key, value in returned_row.items():
                            if not hasattr(instance, key) or getattr(instance, key) is None:
                                setattr(instance, key, value)

                elif instance.__class__.__name__ == 'LocationLead':
                    # Update existing LocationLead instead
                    result = self.supabase.table(table_name).update(data).eq('entity_id', instance.entity_id).eq('state', instance.state).execute()
                    if result.data and len(result.data) > 0:
                        returned_row = result.data[0]
                        if 'id' in returned_row:
                            instance.id = returned_row['id']
                        for key, value in returned_row.items():
                            if not hasattr(instance, key) or getattr(instance, key) is None:
                                setattr(instance, key, value)

                elif instance.__class__.__name__ == 'Entity':
                    # Handle duplicate domain constraint for Entity
                    # Query existing entity by domain and use it instead
                    if hasattr(instance, 'domain') and instance.domain:
                        existing = self.supabase.table(table_name).select("*").eq('domain', instance.domain).limit(1).execute()
                        if existing.data and len(existing.data) > 0:
                            # Use the existing entity's data
                            for key, value in existing.data[0].items():
                                if hasattr(instance, key):
                                    setattr(instance, key, value)
                        else:
                            # Shouldn't happen, but re-raise if we can't find it
                            raise
                    else:
                        raise
                else:
                    # For other tables, re-raise the error
                    raise
            else:
                # For other errors, re-raise
                raise

    def _model_to_dict(self, instance: Any) -> Dict:
        """Convert model instance to dictionary for Supabase."""
        from sqlalchemy import inspect as sqla_inspect

        data = {}

        # Get mapper for this instance to access columns
        mapper = sqla_inspect(instance.__class__)

        # Only iterate over actual database columns
        for column in mapper.columns:
            key = column.key
            value = getattr(instance, key, None)

            # Skip auto-increment IDs if they're None
            if key == 'id' and value is None:
                # Check if this model uses auto-increment ID
                if instance.__class__.__name__ in ['Entity', 'RawEvent', 'LeadCurrent', 'LeadStateHistory', 'LocationLead']:
                    continue

            # Convert datetime to ISO format
            if isinstance(value, datetime):
                value = value.isoformat()

            # Convert UUID to string
            if isinstance(value, uuid.UUID):
                value = str(value)

            # Only include if value is not None or if it's a required field
            if value is not None:
                data[key] = value
            elif key in ['strict', 'dynamic_signals', 'entity_metadata', 'reasons']:
                # These JSONB fields should default to dict/list
                if key in ['dynamic_signals']:
                    data[key] = []
                else:
                    data[key] = {}

        return data


def get_supabase_session() -> SupabaseSession:
    """Get a new Supabase session."""
    return SupabaseSession()
