from typing import List, Dict, Any, Tuple
from thefuzz import process, fuzz
from app.models.migration import MigrationEntityType

class MigrationAIAssistant:
    """
    Provides deterministic and heuristic 'AI' capabilities for the Migration Hub.
    - Field Mapping Suggestions via Fuzzy String Matching
    - Validation explanations
    """
    
    # Target schemas map for suggestions
    TARGET_SCHEMAS = {
        MigrationEntityType.CUSTOMER: ["name", "email", "phone", "address", "city", "state", "zip", "country", "tax_id"],
        MigrationEntityType.VENDOR: ["name", "email", "phone", "address", "company_reg_number", "tax_id", "payment_terms"],
        MigrationEntityType.CHART_OF_ACCOUNTS: ["account_code", "name", "account_type", "normal_balance", "description", "parent_account"],
        MigrationEntityType.ITEM: ["name", "sku", "barcode", "description", "category", "uom", "unit_price", "cost_price", "tax_rate"]
    }

    @classmethod
    def suggest_field_mappings(cls, source_columns: List[str], entity_type: MigrationEntityType) -> Dict[str, Any]:
        """
        Suggests mapping from Source Columns to Target Fields with a confidence score.
        """
        targets = cls.TARGET_SCHEMAS.get(entity_type, [])
        suggestions = []
        
        for source_col in source_columns:
            if not targets:
                continue
                
            # Use fuzz.token_sort_ratio for matching e.g. "Customer Name" -> "name"
            # Special cases / heuristics
            best_match, score = process.extractOne(source_col, targets, scorer=fuzz.token_sort_ratio)
            
            # Boost score for exact substring matches or word matches
            for target in targets:
                if target.lower() in source_col.lower().split() or source_col.lower() in target.lower().split():
                    # If there's an exact word match (e.g. "email" in "Email Address"), override and prioritize it
                    best_match = target
                    score = 95
                    break
            
            if score >= 60:
                suggestions.append({
                    "source_column": source_col,
                    "suggested_target": best_match,
                    "confidence_score": score
                })
            else:
                suggestions.append({
                    "source_column": source_col,
                    "suggested_target": None,
                    "confidence_score": 0
                })
                
        return {
            "entity_type": entity_type,
            "suggestions": suggestions,
            "overall_confidence": sum(s['confidence_score'] for s in suggestions) // len(suggestions) if suggestions else 0
        }
        
    @classmethod
    def explain_validation_error(cls, error_msg: str, row_data: Dict[str, Any]) -> str:
        """
        Provides a human-readable explanation and suggestion for a validation error.
        """
        error_lower = error_msg.lower()
        if "missing mandatory" in error_lower:
            return "A required field is empty. Please provide a valid value or map a default column."
        if "duplicate" in error_lower:
            return "This record already exists in the system. Consider merging or using 'Keep Latest' in the cleansing dashboard."
        if "invalid email" in error_lower:
            return "The email format is incorrect. Ensure it contains an '@' symbol and a valid domain."
        if "invalid currency" in error_lower:
            return "Currency must be numeric. Remove any symbols like '$' or ','."
            
        return "Please review the data format and try again."
