"""
SAI APS Module 1 Assembly Matcher
Matches quote specifications to pre-configured box assemblies
Integrates with QuoteProcessor and provides standalone chatbot functions
"""
import pandas as pd
import json
import logging
from typing import Dict, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)

class Module1Matcher:
    """Match quote specs to Module 1 assemblies"""
    
    def __init__(self, excel_path: str = "Module 1.xlsx"):
        """Initialize with Module_1.xlsx"""
        self.excel_path = excel_path
        self.assemblies = {}
        self.assembly_specs = {}
        self.load_data()
    
    def load_data(self):
        """Load assembly data from Excel"""
        try:
            df = pd.read_excel(self.excel_path)
            
            # Group by Assembly Number
            for assembly_num in df['Assembly Number'].unique():
                assembly_data = df[df['Assembly Number'] == assembly_num]
                
                self.assemblies[assembly_num] = {
                    'components': assembly_data.to_dict('records'),
                    'total_parts': len(assembly_data),
                    'specs': self._infer_specs_from_components(assembly_data)
                }
            
            # Load assembly specifications
            self._load_assembly_specs()
            
            logger.info(f"[MODULE1] Loaded {len(self.assemblies)} assemblies from {self.excel_path}")
            
        except Exception as e:
            logger.error(f"[MODULE1] Failed to load Excel: {e}")
            raise
    
    def _load_assembly_specs(self):
        """Load detailed assembly specifications"""
        # Hard-coded specifications based on the training document
        self.assembly_specs = {
            '123456-0100-101': {
                'height': '90',
                'width': '40',
                'depth': '60',
                'breaker_type': 'ABB SACE Emax 6.2',
                'breaker_quantity': 1,
                'mount': 'Fixed',
                'access': 'Front and rear',
                'project': 'UL891-S41A Section 101'
            },
            '123456-0100-102': {
                'height': '90',
                'width': '40',
                'depth': '60',
                'breaker_type': 'ABB SACE Emax 2.2',
                'breaker_quantity': 3,
                'mount': 'Fixed',
                'access': 'Front and rear',
                'project': 'UL891-S41A Section 102'
            },
            '123456-0100-103': {
                'height': '90',
                'width': '40',
                'depth': '60',
                'breaker_type': 'ABB SACE Emax 2.2',
                'breaker_quantity': 2,
                'mount': 'Fixed',
                'access': 'Front and rear',
                'project': 'UL891-S41A Section 103'
            },
            '123456-0100-201': {
                'height': '90',
                'width': '40',
                'depth': '60',
                'breaker_type': 'ABB SACE Emax 6.2',
                'breaker_quantity': 1,
                'mount': 'Drawout',
                'access': 'Front only',
                'project': 'UL891-S41B Section 101'
            },
            '123456-0100-202': {
                'height': '90',
                'width': '40',
                'depth': '60',
                'breaker_type': 'ABB SACE Emax 2.2',
                'breaker_quantity': 1,
                'mount': 'Drawout',
                'access': 'Front only',
                'project': 'UL891-S41B Section 102'
            },
            '123456-0100-203': {
                'height': '90',
                'width': '40',
                'depth': '60',
                'breaker_type': 'ABB SACE Emax 2.2',
                'breaker_quantity': 2,
                'mount': 'Drawout',
                'access': 'Front only',
                'project': 'UL891-S41B Section 103'
            },
            '123456-0100-204': {
                'height': '90',
                'width': '42',
                'depth': '60',
                'breaker_type': 'ABB SACE Tmax',
                'breaker_quantity': 'multiple',
                'mount': 'Fixed',
                'access': 'Front only',
                'project': 'UL891-S41B Section 104'
            },
            '123456-0100-301': {
                'height': '90',
                'width': '30',
                'depth': '48',
                'breaker_type': 'ABB SACE Emax 2.2',
                'breaker_quantity': 1,
                'mount': 'Drawout',
                'access': 'Front and rear',
                'project': 'UL891-S4S1 Section 101'
            },
            '123456-0100-302': {
                'height': '90',
                'width': '42',
                'depth': '48',
                'breaker_type': 'ABB SACE Tmax',
                'breaker_quantity': 'multiple',
                'mount': 'Fixed',
                'access': 'Front and rear',
                'project': 'UL891-S4S1 Section 102'
            },
            '123456-0100-401': {
                'height': '78',
                'width': '42',
                'depth': '33',
                'breaker_type': 'Square D',
                'breaker_quantity': 'multiple',
                'mount': 'Fixed',
                'access': 'Front only',
                'project': '400kW GVX Section 101'
            }
        }
    
    def _infer_specs_from_components(self, components_df) -> Dict:
        """Infer specifications from component descriptions"""
        specs = {
            'widths': set(),
            'heights': set(),
            'depths': set(),
            'breakers': [],
            'seismic': False,
            'mount_types': set()
        }
        
        for _, row in components_df.iterrows():
            desc = str(row.get('Description', '')).upper()
            
            # Extract dimensions
            width_match = re.search(r'(\d+)W', desc)
            if width_match:
                specs['widths'].add(width_match.group(1))
            
            height_match = re.search(r'(\d+)H', desc)
            if height_match:
                specs['heights'].add(height_match.group(1))
            
            depth_match = re.search(r'(\d+)\s*D', desc)
            if depth_match:
                specs['depths'].add(depth_match.group(1))
            
            # Check for breakers
            if 'EMAX' in desc or 'TMAX' in desc or 'SQUARE D' in desc:
                specs['breakers'].append(desc)
            
            # Check for seismic
            if 'SEISMIC' in desc:
                specs['seismic'] = True
            
            # Check for mount type
            if 'FIXED' in desc:
                specs['mount_types'].add('Fixed')
            if 'DRAWOUT' in desc:
                specs['mount_types'].add('Drawout')
        
        return specs
    
    def extract_features_from_quote(self, quote_json: Dict) -> Dict:
        """Extract features from parsed quote JSON"""
        features = {
            'height': None,
            'width': None,
            'depth': None,
            'breaker_type': None,
            'breaker_quantity': None,
            'access': None,
            'mount': None
        }
        
        # Extract from sections
        sections = quote_json.get('sections', [])
        if sections:
            # Get first section's dimensions
            first_section = sections[0]
            dims = first_section.get('dimensions', {})
            
            if isinstance(dims, dict):
                features['height'] = self._normalize_dimension(dims.get('height', ''))
                features['width'] = self._normalize_dimension(dims.get('width', ''))
                features['depth'] = self._normalize_dimension(dims.get('depth', ''))
            
            # Get breaker info
            main_breaker = first_section.get('main_circuit_breaker', {})
            breakers = first_section.get('breakers', [])
            
            if main_breaker:
                features['breaker_type'] = main_breaker.get('type', '')
                features['breaker_quantity'] = 1
            elif breakers:
                features['breaker_type'] = breakers[0].get('type', '')
                features['breaker_quantity'] = len(breakers)
        
        # Check for access type in requirements
        requirements = quote_json.get('special_construction_requirements', [])
        req_text = ' '.join(str(r) for r in requirements).lower()
        
        if 'front and rear' in req_text or 'rear access' in req_text:
            features['access'] = 'Front and rear'
        elif 'front access' in req_text or 'front only' in req_text:
            features['access'] = 'Front only'
        
        # Check for mount type
        if 'drawout' in req_text or 'draw-out' in req_text:
            features['mount'] = 'Drawout'
        elif 'fixed' in req_text:
            features['mount'] = 'Fixed'
        
        return features
    
    def _normalize_dimension(self, dim_str: str) -> Optional[str]:
        """Extract numeric dimension from string"""
        if not dim_str:
            return None
        
        # Extract numbers
        match = re.search(r'(\d+)', str(dim_str))
        if match:
            return match.group(1)
        return None
    
    def _normalize_breaker_type(self, breaker_str: str) -> str:
        """Normalize breaker type for matching"""
        if not breaker_str:
            return ""
        
        breaker_upper = breaker_str.upper()
        
        # Check for specific models
        if 'EMAX 6.2' in breaker_upper or 'E6.2' in breaker_upper:
            return 'ABB SACE Emax 6.2'
        elif 'EMAX 4.2' in breaker_upper or 'E4.2' in breaker_upper:
            return 'ABB SACE Emax 4.2'
        elif 'EMAX 2.2' in breaker_upper or 'E2.2' in breaker_upper:
            return 'ABB SACE Emax 2.2'
        elif 'TMAX' in breaker_upper:
            return 'ABB SACE Tmax'
        elif 'SQUARE D' in breaker_upper:
            return 'Square D'
        
        return breaker_str
    
    def match_assembly(self, features: Dict) -> Tuple[List[str], str, str]:
        """
        Match features to assemblies
        Returns: (matched_assemblies, status, message)
        Status: 'exact_match', 'ambiguous', 'no_match'
        """
        matches = []
        
        # Normalize breaker type
        if features.get('breaker_type'):
            features['breaker_type'] = self._normalize_breaker_type(features['breaker_type'])
        
        # Check each assembly
        for assembly_num, specs in self.assembly_specs.items():
            if self._features_match(features, specs):
                matches.append(assembly_num)
        
        # Determine status
        if len(matches) == 1:
            assembly = matches[0]
            total_parts = self.assemblies[assembly]['total_parts']
            project = self.assembly_specs[assembly]['project']
            
            message = (f"✅ Found exact match: Assembly {assembly}\n"
                      f"   Project: {project}\n"
                      f"   Total parts: {total_parts}")
            
            return matches, 'exact_match', message
        
        elif len(matches) > 1:
            message = (f"⚠️ Found {len(matches)} assemblies matching your specs.\n"
                      f"   Assemblies: {', '.join(matches)}\n"
                      f"   Please specify:\n"
                      f"   • Access type: Front only OR Front and rear?\n"
                      f"   • Mount type: Fixed OR Drawout?")
            
            return matches, 'ambiguous', message
        
        else:
            # Find closest matches
            closest = self._find_closest_matches(features, top_n=3)
            
            message = (f"❌ No exact match found.\n"
                      f"   Closest options:\n")
            
            for asm, score in closest:
                specs = self.assembly_specs[asm]
                message += (f"   • {asm}: {specs['height']}\"H x {specs['width']}\"W x {specs['depth']}\"D, "
                          f"{specs['breaker_type']}\n")
            
            return [], 'no_match', message
    
    def _features_match(self, features: Dict, specs: Dict) -> bool:
        """Check if all features match"""
        # Required matches
        if features.get('height') and features['height'] != specs['height']:
            return False
        
        if features.get('width') and features['width'] != specs['width']:
            return False
        
        if features.get('depth') and features['depth'] != specs['depth']:
            return False
        
        # Breaker type match
        if features.get('breaker_type'):
            feature_breaker = features['breaker_type'].upper()
            spec_breaker = specs['breaker_type'].upper()
            
            # Check if breaker types are compatible
            if not self._breaker_compatible(feature_breaker, spec_breaker):
                return False
        
        # Breaker quantity (if specified and not 'multiple')
        if features.get('breaker_quantity') and specs['breaker_quantity'] != 'multiple':
            if features['breaker_quantity'] != specs['breaker_quantity']:
                return False
        
        # Access type (if specified)
        if features.get('access'):
            if features['access'].lower() != specs['access'].lower():
                return False
        
        # Mount type (if specified)
        if features.get('mount'):
            if features['mount'].lower() != specs['mount'].lower():
                return False
        
        return True
    
    def _breaker_compatible(self, feature_breaker: str, spec_breaker: str) -> bool:
        """Check if breaker types are compatible"""
        # Exact match
        if feature_breaker == spec_breaker:
            return True
        
        # Check if key terms match
        feature_terms = set(feature_breaker.split())
        spec_terms = set(spec_breaker.split())
        
        # Must have common manufacturer and model
        if 'ABB' in feature_terms and 'ABB' in spec_terms:
            if 'EMAX' in feature_terms and 'EMAX' in spec_terms:
                return True
            if 'TMAX' in feature_terms and 'TMAX' in spec_terms:
                return True
        
        if 'SQUARE' in feature_terms and 'SQUARE' in spec_terms:
            return True
        
        return False
    
    def _find_closest_matches(self, features: Dict, top_n: int = 3) -> List[Tuple[str, int]]:
        """Find closest matching assemblies"""
        scores = []
        
        for assembly_num, specs in self.assembly_specs.items():
            score = 0
            
            # Score dimensions
            if features.get('height') == specs['height']:
                score += 3
            if features.get('width') == specs['width']:
                score += 3
            if features.get('depth') == specs['depth']:
                score += 3
            
            # Score breaker
            if features.get('breaker_type'):
                if self._breaker_compatible(
                    features['breaker_type'].upper(),
                    specs['breaker_type'].upper()
                ):
                    score += 2
            
            scores.append((assembly_num, score))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_n]
    
    def generate_bom(self, assembly_num: str) -> Dict:
        """Generate BOM for an assembly"""
        if assembly_num not in self.assemblies:
            return {
                'error': f'Assembly {assembly_num} not found',
                'available_assemblies': list(self.assemblies.keys())
            }
        
        assembly_data = self.assemblies[assembly_num]
        
        bom = {
            'assembly_number': assembly_num,
            'project': self.assembly_specs[assembly_num]['project'],
            'specifications': self.assembly_specs[assembly_num],
            'total_parts': assembly_data['total_parts'],
            'components': []
        }
        
        for component in assembly_data['components']:
            bom['components'].append({
                'part_number': component.get('Component Part Number', ''),
                'description': component.get('Description', ''),
                'quantity': component.get('Quantity Per', 0),
                'sequence': component.get('Item & BOM Sequence Number', 0)
            })
        
        return bom


# Standalone functions for chatbot integration
_matcher = None

def get_matcher():
    """Get or create matcher instance"""
    global _matcher
    if _matcher is None:
        _matcher = Module1Matcher()
    return _matcher


def match_quote_to_assembly(quote_json: Dict) -> Dict:
    """
    Main function to match a quote to an assembly
    Used by QuoteProcessor and chatbot
    """
    try:
        matcher = get_matcher()
        
        # Extract features
        features = matcher.extract_features_from_quote(quote_json)
        
        # Match assembly
        assemblies, status, message = matcher.match_assembly(features)
        
        # Generate BOM if exact match
        bom = None
        if status == 'exact_match' and assemblies:
            bom = matcher.generate_bom(assemblies[0])
        
        return {
            'status': status,
            'message': message,
            'matched_assemblies': assemblies,
            'extracted_features': features,
            'bom': bom
        }
        
    except Exception as e:
        logger.error(f"[MODULE1] Matching failed: {e}")
        return {
            'status': 'error',
            'message': f'Error during matching: {str(e)}',
            'matched_assemblies': [],
            'extracted_features': {},
            'bom': None
        }


def match_from_user_input(user_input: str) -> Dict:
    """
    Match from user's text input (for chatbot)
    Example: "90 inches high, 40 wide, 60 deep, ABB Emax 6.2"
    """
    try:
        # Simple parsing of user input
        features = {
            'height': None,
            'width': None,
            'depth': None,
            'breaker_type': None,
            'breaker_quantity': None,
            'access': None,
            'mount': None
        }
        
        user_upper = user_input.upper()
        
        # Extract dimensions
        height_match = re.search(r'(\d+)\s*(?:INCH|IN|"|\')*\s*(?:H|HIGH|HEIGHT)', user_upper)
        if height_match:
            features['height'] = height_match.group(1)
        
        width_match = re.search(r'(\d+)\s*(?:INCH|IN|"|\')*\s*(?:W|WIDE|WIDTH)', user_upper)
        if width_match:
            features['width'] = width_match.group(1)
        
        depth_match = re.search(r'(\d+)\s*(?:INCH|IN|"|\')*\s*(?:D|DEEP|DEPTH)', user_upper)
        if depth_match:
            features['depth'] = depth_match.group(1)
        
        # Extract breaker
        if 'EMAX 6.2' in user_upper:
            features['breaker_type'] = 'ABB SACE Emax 6.2'
        elif 'EMAX 2.2' in user_upper:
            features['breaker_type'] = 'ABB SACE Emax 2.2'
        elif 'TMAX' in user_upper:
            features['breaker_type'] = 'ABB SACE Tmax'
        elif 'SQUARE D' in user_upper:
            features['breaker_type'] = 'Square D'
        
        # Extract quantity
        qty_match = re.search(r'(\d+)\s*(?:X\s*)?(?:EMAX|TMAX|BREAKER)', user_upper)
        if qty_match:
            features['breaker_quantity'] = int(qty_match.group(1))
        
        # Extract access type
        if 'FRONT AND REAR' in user_upper or 'REAR ACCESS' in user_upper:
            features['access'] = 'Front and rear'
        elif 'FRONT ONLY' in user_upper or 'FRONT ACCESS' in user_upper:
            features['access'] = 'Front only'
        
        # Extract mount type
        if 'DRAWOUT' in user_upper or 'DRAW-OUT' in user_upper:
            features['mount'] = 'Drawout'
        elif 'FIXED' in user_upper:
            features['mount'] = 'Fixed'
        
        # Match
        matcher = get_matcher()
        assemblies, status, message = matcher.match_assembly(features)
        
        # Generate BOM if exact match
        bom = None
        if status == 'exact_match' and assemblies:
            bom = matcher.generate_bom(assemblies[0])
        
        return {
            'status': status,
            'message': message,
            'matched_assemblies': assemblies,
            'extracted_features': features,
            'bom': bom
        }
        
    except Exception as e:
        logger.error(f"[MODULE1] User input matching failed: {e}")
        return {
            'status': 'error',
            'message': f'Error parsing input: {str(e)}',
            'matched_assemblies': [],
            'extracted_features': {},
            'bom': None
        }
