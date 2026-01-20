"""Fuzzy matching utilities for company name deduplication."""

import re
from difflib import SequenceMatcher
from typing import Optional, Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.company_history import CompanyRecord


# Common company suffixes to remove during normalization
COMPANY_SUFFIXES = [
    r'\s+incorporated$',
    r'\s+corporation$',
    r'\s+company$',
    r'\s+limited$',
    r'\s+inc\.?$',
    r'\s+llc\.?$',
    r'\s+ltd\.?$',
    r'\s+corp\.?$',
    r'\s+co\.?$',
    r'\s+plc\.?$',
    r'\s+sa\.?$',
    r'\s+ag\.?$',
    r'\s+gmbh\.?$',
    r'\s+therapeutics$',
    r'\s+pharmaceuticals$',
    r'\s+pharma$',
    r'\s+biopharma$',
    r'\s+biosciences$',
    r'\s+biotherapeutics$',
    r'\s+biotech$',
    r'\s+biotechnology$',
    r'\s+sciences$',
    r'\s+medical$',
    r'\s+health$',
    r'\s+healthcare$',
]

# Default matching threshold (85%)
DEFAULT_MATCH_THRESHOLD = 85


def normalize_company_name(name: str) -> str:
    """
    Normalize a company name for consistent matching.
    
    Rules:
    - Convert to lowercase
    - Remove common suffixes (Inc, LLC, Ltd, Corp, Therapeutics, etc.)
    - Remove all punctuation and whitespace
    - Example: "Radiant Therapeutics, Inc." -> "radiant"
    
    Args:
        name: Original company name
        
    Returns:
        Normalized name string
    """
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower().strip()
    
    # Remove common suffixes (order matters - remove longer ones first)
    for suffix_pattern in COMPANY_SUFFIXES:
        normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove parenthetical content like "(formerly XYZ)"
    normalized = re.sub(r'\s*\([^)]*\)\s*', '', normalized)
    
    # Remove punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Remove all whitespace
    normalized = re.sub(r'\s+', '', normalized)
    
    return normalized


def fuzzy_match_score(name1: str, name2: str) -> int:
    """
    Calculate similarity score between two strings.
    
    Uses Python's difflib SequenceMatcher which is based on the
    Ratcliff/Obershelp algorithm.
    
    Args:
        name1: First string to compare
        name2: Second string to compare
        
    Returns:
        Similarity score from 0 to 100
    """
    if not name1 or not name2:
        return 0
    
    # Normalize both names for comparison
    norm1 = normalize_company_name(name1)
    norm2 = normalize_company_name(name2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return 100
    
    # Use SequenceMatcher for fuzzy comparison
    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    
    return int(ratio * 100)


def is_fuzzy_match(name1: str, name2: str, threshold: int = DEFAULT_MATCH_THRESHOLD) -> bool:
    """
    Check if two company names are considered a match.
    
    Args:
        name1: First company name
        name2: Second company name
        threshold: Minimum similarity score (0-100) to be considered a match
        
    Returns:
        True if names match above threshold
    """
    return fuzzy_match_score(name1, name2) >= threshold


def find_best_match(
    company_name: str,
    company_records: List["CompanyRecord"],
    threshold: int = DEFAULT_MATCH_THRESHOLD
) -> Tuple[Optional["CompanyRecord"], int]:
    """
    Find the best matching company in the history.
    
    Args:
        company_name: Name to search for
        company_records: List of CompanyRecord objects to search
        threshold: Minimum score to be considered a match
        
    Returns:
        Tuple of (best_matching_record, match_score)
        Returns (None, 0) if no match found above threshold
    """
    if not company_name or not company_records:
        return None, 0
    
    normalized_search = normalize_company_name(company_name)
    
    best_match: Optional["CompanyRecord"] = None
    best_score = 0
    
    for record in company_records:
        # First check exact normalized match (fastest)
        if record.normalized_name == normalized_search:
            return record, 100
        
        # Calculate fuzzy score
        score = fuzzy_match_score(company_name, record.company_name)
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = record
    
    return best_match, best_score


def get_match_confidence(score: int) -> str:
    """
    Get human-readable confidence level for a match score.
    
    Args:
        score: Match score 0-100
        
    Returns:
        Confidence level string
    """
    if score >= 100:
        return "exact"
    elif score >= 95:
        return "very_high"
    elif score >= 90:
        return "high"
    elif score >= 85:
        return "moderate"
    elif score >= 75:
        return "low"
    else:
        return "no_match"
