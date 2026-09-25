import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class EvidenceItem:
    def __init__(
        self,
        evidence_id: str,
        evidence_type: str,
        source: str,
        summary: str,
        data: Any
    ):
        self.evidence_id = evidence_id
        self.evidence_type = evidence_type
        self.source = source
        self.summary = summary
        self.data = data
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source": self.source,
            "summary": self.summary,
            "data": self.data,
            "timestamp": self.timestamp,
        }

class EvidenceBundle:
    def __init__(self, failure_id: str):
        self.failure_id = failure_id
        self.items: List[EvidenceItem] = []
        self._id_counter = 1

    def add_item(self, evidence_type: str, source: str, summary: str, data: Any) -> str:
        evidence_id = f"EV-{evidence_type[:4].upper()}-{self._id_counter:02d}"
        self._id_counter += 1
        item = EvidenceItem(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            source=source,
            summary=summary,
            data=data
        )
        self.items.append(item)
        return evidence_id

    def get_valid_ids(self) -> List[str]:
        return [item.evidence_id for item in self.items]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "total_items": len(self.items),
            "evidence_items": [item.to_dict() for item in self.items],
            "valid_evidence_ids": self.get_valid_ids()
        }
