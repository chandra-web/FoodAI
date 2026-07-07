from typing import Dict, Any

MEDICAL_DISCLAIMER = (
    "Disclaimer: This information is for educational purposes only and is not a substitute "
    "for professional medical advice, diagnosis, or treatment. Always consult your physician "
    "or a qualified health provider with any questions you may have regarding a medical condition."
)

HARMFUL_TERMS = ["starve", "fast for days", "extreme diet", "eat nothing"]

def apply_safety_filters(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Filters harmful recommendations and ensures medical disclaimers are present."""
    
    # 1. Filter harmful recommendations
    if "recommendations" in response_data:
        filtered_recs = []
        for rec in response_data["recommendations"]:
            is_safe = True
            rec_lower = str(rec).lower()
            for term in HARMFUL_TERMS:
                if term in rec_lower:
                    is_safe = False
                    break
            if is_safe:
                filtered_recs.append(rec)
            else:
                filtered_recs.append("This recommendation was removed due to safety guidelines.")
        response_data["recommendations"] = filtered_recs

    # 2. Add medical disclaimer
    if "disclaimer" not in response_data:
        response_data["disclaimer"] = MEDICAL_DISCLAIMER
        
    return response_data
