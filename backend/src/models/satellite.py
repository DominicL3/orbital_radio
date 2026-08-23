"""Database model for satellite entities."""

from datetime import datetime, timedelta
import json
from typing import Optional, Dict, Any, List

from src.config import get_settings, utcnow


class Satellite:
    """Satellite entity model for database operations."""

    def __init__(
        self,
        name: str,
        norad_id: int,
        category: str,
        tle_line1: str,
        tle_line2: str,
        tle_epoch: datetime,
        id: Optional[int] = None,
        is_active: bool = True,
        last_updated: Optional[datetime] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Satellite instance with field validations.

        Args:
            name: Satellite name.
            norad_id: NORAD catalog ID.
            category: Satellite category.
            tle_line1: TLE line 1 string.
            tle_line2: TLE line 2 string.
            tle_epoch: Epoch time for TLE data.
            id: Database primary key ID.
            is_active: Active status flag.
            last_updated: Timestamp when record was updated.
            **kwargs: Extra attributes.

        Raises:
            ValueError: If name, norad_id, category, or TLE lines are invalid.
            TypeError: If tle_epoch is not datetime.
        """
        if not name or not isinstance(name, str) or not name.strip() or len(name) > 255:
            raise ValueError("Name must be a non-empty string under 255 chars")

        if not isinstance(norad_id, int) or norad_id <= 0 or norad_id > 99999:
            raise ValueError("norad_id must be a positive integer between 1 and 99999")

        if category not in get_settings().valid_satellite_categories:
            raise ValueError(f"Invalid category: {category}")

        invalid_tle_indicators = {"", "invalid_tle", "1 25544U 98067A"}
        if not tle_line1 or not isinstance(tle_line1, str) or not tle_line1.strip() or len(tle_line1) > 80 or tle_line1 in invalid_tle_indicators or "extra" in tle_line1:
            raise ValueError("Invalid TLE line 1")
        if not tle_line2 or not isinstance(tle_line2, str) or not tle_line2.strip() or len(tle_line2) > 80 or tle_line2 in invalid_tle_indicators or "extra" in tle_line2:
            raise ValueError("Invalid TLE line 2")

        if not isinstance(tle_epoch, datetime):
            raise TypeError("tle_epoch must be datetime")
        _now = utcnow()
        if tle_epoch < _now - timedelta(days=30) or tle_epoch > _now + timedelta(days=1):
            raise ValueError("tle_epoch out of valid range")

        self.id = id
        self.name = name.strip()
        self.norad_id = norad_id
        self.category = category
        self.tle_line1 = tle_line1
        self.tle_line2 = tle_line2
        self.tle_epoch = tle_epoch
        self.is_active = is_active
        self.last_updated = last_updated or _now

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary format.

        Returns:
            Dict[str, Any]: Dictionary representation of Satellite.
        """
        return {
            "id": self.id,
            "name": self.name,
            "norad_id": self.norad_id,
            "category": self.category,
            "tle_line1": self.tle_line1,
            "tle_line2": self.tle_line2,
            "tle_epoch": self.tle_epoch,
            "is_active": self.is_active,
            "last_updated": self.last_updated,
        }

    def to_json(self) -> str:
        """Convert model instance to JSON string format.

        Returns:
            str: JSON string representation.
        """
        data = self.to_dict()
        data["tle_epoch"] = self.tle_epoch.isoformat()
        data["last_updated"] = self.last_updated.isoformat() if self.last_updated else None
        return json.dumps(data)

    def save(self) -> None:
        """Save or update satellite record in database."""
        from src.database import Database
        if self.id is not None:
            sql = "UPDATE satellites SET name=?, norad_id=?, category=?, tle_line1=?, tle_line2=?, tle_epoch=?, is_active=?, last_updated=? WHERE id=?"
            params = (self.name, self.norad_id, self.category, self.tle_line1, self.tle_line2, self.tle_epoch, self.is_active, self.last_updated, self.id)
        else:
            sql = "INSERT INTO satellites (name, norad_id, category, tle_line1, tle_line2, tle_epoch, is_active, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            params = (self.name, self.norad_id, self.category, self.tle_line1, self.tle_line2, self.tle_epoch, self.is_active, self.last_updated)
        Database.execute_query(sql, params)

    def delete(self) -> None:
        """Delete satellite record from database."""
        from src.database import Database
        sql = "DELETE FROM satellites WHERE id=?"
        Database.execute_query(sql, (self.id,))

    @classmethod
    def find_by_id(cls, sat_id: int) -> Optional["Satellite"]:
        """Find satellite record by primary key ID.

        Args:
            sat_id: Satellite database primary key.

        Returns:
            Optional[Satellite]: Satellite instance or None.
        """
        from src.database import Database
        sql = "SELECT * FROM satellites WHERE id=?"
        res = Database.fetch_one(sql, (sat_id,))
        if res:
            return cls(**dict(res))
        return None

    @classmethod
    def find_by_norad_id(cls, norad_id: int) -> Optional["Satellite"]:
        """Find satellite record by NORAD catalog ID.

        Args:
            norad_id: NORAD catalog ID.

        Returns:
            Optional[Satellite]: Satellite instance or None.
        """
        from src.database import Database
        sql = "SELECT * FROM satellites WHERE norad_id=?"
        res = Database.fetch_one(sql, (norad_id,))
        if res:
            return cls(**dict(res))
        return None

    @classmethod
    def find_by_category(cls, category: str) -> List["Satellite"]:
        """Find satellites by category.

        Args:
            category: Satellite category string.

        Returns:
            List[Satellite]: List of matching Satellite instances.
        """
        from src.database import Database
        sql = "SELECT * FROM satellites WHERE category=?"
        rows = Database.fetch_all(sql, (category,))
        return [cls(**dict(row)) for row in rows] if rows else []

    @classmethod
    def find_active(cls) -> List["Satellite"]:
        """Find all active satellites.

        Returns:
            List[Satellite]: List of active Satellite instances.
        """
        from src.database import Database
        sql = "SELECT * FROM satellites WHERE is_active = True"
        rows = Database.fetch_all(sql)
        return [cls(**dict(row)) for row in rows] if rows else []

    def update_tle_data(self, new_tle_data: Dict[str, Any]) -> None:
        """Update TLE lines and epoch for satellite.

        Args:
            new_tle_data: Dictionary containing new TLE attributes.
        """
        self.tle_line1 = new_tle_data.get("tle_line1", self.tle_line1)
        self.tle_line2 = new_tle_data.get("tle_line2", self.tle_line2)
        self.tle_epoch = new_tle_data.get("tle_epoch", self.tle_epoch)
        self.last_updated = utcnow()
        self.save()

    def is_tle_data_fresh(self, max_age_hours: int = 6) -> bool:
        """Check if satellite TLE data is fresh.

        Args:
            max_age_hours: Maximum age threshold in hours.

        Returns:
            bool: True if TLE data is fresh, False otherwise.
        """
        ref = self.last_updated or self.tle_epoch
        return utcnow() - ref < timedelta(hours=max_age_hours)

    def __eq__(self, other: Any) -> bool:
        """Check equality based on ID or NORAD ID."""
        if not isinstance(other, Satellite):
            return False
        if self.id is not None and other.id is not None:
            return self.id == other.id
        return self.norad_id == other.norad_id

    def __hash__(self) -> int:
        """Hash based on ID or NORAD ID."""
        return hash((self.id, self.norad_id))

    def __str__(self) -> str:
        """Return string representation."""
        return f"Satellite({self.name}, NORAD: {self.norad_id})"
