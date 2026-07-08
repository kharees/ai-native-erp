import re
from typing import Dict, Any, List, Tuple
from thefuzz import fuzz

class DataCleansingEngine:
    
    @staticmethod
    def validate_format(field_name: str, value: Any) -> List[str]:
        """
        Validates data formats like email, phone, currency.
        Returns a list of error messages (empty if valid).
        """
        if value is None or str(value).strip() == "":
            return []
            
        errors = []
        val_str = str(value).strip()
        
        # Email Validation
        if "email" in field_name.lower():
            if not re.match(r"[^@]+@[^@]+\.[^@]+", val_str):
                errors.append(f"Invalid email format in field '{field_name}'")
                
        # Phone Validation (Basic)
        elif "phone" in field_name.lower() or "contact" in field_name.lower():
            # Just check if it has digits
            if not any(char.isdigit() for char in val_str):
                errors.append(f"Invalid phone format in field '{field_name}' - no digits found")
                
        # Currency/Numeric
        elif any(keyword in field_name.lower() for keyword in ["price", "cost", "amount", "balance"]):
            try:
                # Strip common currency symbols before check
                clean_val = val_str.replace("$", "").replace(",", "").strip()
                float(clean_val)
            except ValueError:
                errors.append(f"Invalid numeric/currency format in field '{field_name}'")
                
        return errors

    @staticmethod
    def apply_transformations(data: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applies transformation rules: rename, value_map, etc.
        rules format:
        [
            {"type": "RENAME", "source": "OldName", "target": "NewName"},
            {"type": "UPPERCASE", "field": "name"}
        ]
        """
        transformed = data.copy()
        
        for rule in rules:
            rtype = rule.get("type")
            
            if rtype == "RENAME":
                src = rule.get("source")
                tgt = rule.get("target")
                if src in transformed:
                    transformed[tgt] = transformed.pop(src)
                    
            elif rtype == "UPPERCASE":
                fld = rule.get("field")
                if fld in transformed and isinstance(transformed[fld], str):
                    transformed[fld] = transformed[fld].upper()
                    
            elif rtype == "STRIP_CURRENCY":
                fld = rule.get("field")
                if fld in transformed and isinstance(transformed[fld], str):
                    transformed[fld] = transformed[fld].replace("$", "").replace(",", "").strip()
                    
        return transformed

    @staticmethod
    def detect_duplicates(records: List[Dict[str, Any]], match_fields: List[str], threshold: int = 85) -> List[Dict[str, Any]]:
        """
        Detects duplicates within the provided list of mapped records.
        Returns a list of duplicate clusters.
        """
        duplicate_clusters = []
        processed_indices = set()
        
        for i, rec1 in enumerate(records):
            if i in processed_indices:
                continue
                
            cluster = [i]
            
            for j in range(i + 1, len(records)):
                if j in processed_indices:
                    continue
                    
                rec2 = records[j]
                
                # Check match fields
                total_score = 0
                fields_compared = 0
                
                for field in match_fields:
                    val1 = str(rec1.get(field, "")).strip().lower()
                    val2 = str(rec2.get(field, "")).strip().lower()
                    
                    if not val1 and not val2:
                        continue
                        
                    if val1 == val2:
                        total_score += 100
                    else:
                        total_score += fuzz.token_sort_ratio(val1, val2)
                    fields_compared += 1
                    
                if fields_compared > 0:
                    avg_score = total_score / fields_compared
                    if avg_score >= threshold:
                        cluster.append(j)
                        
            if len(cluster) > 1:
                duplicate_clusters.append({
                    "primary_index": cluster[0],
                    "duplicate_indices": cluster[1:]
                })
                processed_indices.update(cluster)
                
        return duplicate_clusters
