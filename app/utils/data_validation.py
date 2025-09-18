"""
FloatChat - Data Validation Framework

Comprehensive data validation and quality assurance for ARGO oceanographic data.
Includes validation rules, anomaly detection, and quality scoring.
"""

import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationRule:
    """Data validation rule definition."""
    name: str
    description: str
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'format', 'range', 'consistency', 'completeness'


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule: ValidationRule
    passed: bool
    message: str
    value: Any = None
    expected: Any = None


class ArgoDataValidator:
    """Comprehensive ARGO data validation and quality assessment."""
    
    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()
        
    def _initialize_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """Initialize validation rules for different data types."""
        
        rules = {
            'float': [
                ValidationRule(
                    name="wmo_id_format",
                    description="WMO ID should be 7-10 digit number",
                    severity="error",
                    category="format"
                ),
                ValidationRule(
                    name="platform_number_present",
                    description="Platform number must be present",
                    severity="error",
                    category="completeness"
                ),
                ValidationRule(
                    name="float_type_valid",
                    description="Float type should be recognized type",
                    severity="warning",
                    category="format"
                ),
                ValidationRule(
                    name="deployment_location_valid",
                    description="Deployment location should be within valid ocean bounds",
                    severity="error",
                    category="range"
                )
            ],
            
            'profile': [
                ValidationRule(
                    name="latitude_range",
                    description="Latitude must be between -90 and 90 degrees",
                    severity="error",
                    category="range"
                ),
                ValidationRule(
                    name="longitude_range",
                    description="Longitude must be between -180 and 180 degrees",
                    severity="error",
                    category="range"
                ),
                ValidationRule(
                    name="profile_date_reasonable",
                    description="Profile date should be reasonable (after 1990, not future)",
                    severity="error",
                    category="range"
                ),
                ValidationRule(
                    name="cycle_number_positive",
                    description="Cycle number should be positive integer",
                    severity="error",
                    category="format"
                ),
                ValidationRule(
                    name="location_over_ocean",
                    description="Profile location should be over ocean (depth > 200m)",
                    severity="warning",
                    category="consistency"
                ),
                ValidationRule(
                    name="temperature_range_reasonable",
                    description="Temperature range should be oceanographically reasonable",
                    severity="warning",
                    category="range"
                ),
                ValidationRule(
                    name="salinity_range_reasonable",
                    description="Salinity range should be oceanographically reasonable",
                    severity="warning",
                    category="range"
                )
            ],
            
            'measurement': [
                ValidationRule(
                    name="pressure_positive",
                    description="Pressure should be positive",
                    severity="error",
                    category="range"
                ),
                ValidationRule(
                    name="pressure_increasing",
                    description="Pressure should generally increase with depth",
                    severity="warning",
                    category="consistency"
                ),
                ValidationRule(
                    name="temperature_ocean_range",
                    description="Temperature should be within ocean range (-2 to 40°C)",
                    severity="error",
                    category="range"
                ),
                ValidationRule(
                    name="salinity_ocean_range",
                    description="Salinity should be within ocean range (0 to 50 PSU)",
                    severity="error",
                    category="range"
                ),
                ValidationRule(
                    name="oxygen_positive",
                    description="Oxygen concentration should be positive",
                    severity="warning",
                    category="range"
                ),
                ValidationRule(
                    name="temperature_salinity_consistency",
                    description="Temperature and salinity should be consistent with water masses",
                    severity="info",
                    category="consistency"
                ),
                ValidationRule(
                    name="quality_flag_valid",
                    description="Quality flags should be valid ARGO QC values",
                    severity="warning",
                    category="format"
                )
            ]
        }
        
        return rules
    
    async def validate_float_data(self, float_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate ARGO float metadata.
        
        Args:
            float_data: Float metadata dictionary
            
        Returns:
            Dict containing validation results
        """
        try:
            results = []
            
            # Apply float validation rules
            for rule in self.validation_rules['float']:
                result = self._apply_float_rule(rule, float_data)
                results.append(result)
            
            # Calculate quality score
            quality_score = self._calculate_validation_score(results)
            
            # Generate summary
            summary = self._generate_validation_summary(results)
            
            return {
                "data_type": "float",
                "wmo_id": float_data.get("wmo_id", "unknown"),
                "validation_results": [self._result_to_dict(r) for r in results],
                "quality_score": quality_score,
                "summary": summary,
                "validation_timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("Float validation failed", error=str(e), exc_info=True)
            return {
                "data_type": "float",
                "validation_error": str(e),
                "quality_score": 0.0
            }
    
    async def validate_profile_data(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate ARGO profile data.
        
        Args:
            profile_data: Profile data dictionary
            
        Returns:
            Dict containing validation results
        """
        try:
            results = []
            
            # Apply profile validation rules
            for rule in self.validation_rules['profile']:
                result = self._apply_profile_rule(rule, profile_data)
                results.append(result)
            
            # Calculate quality score
            quality_score = self._calculate_validation_score(results)
            
            # Generate summary
            summary = self._generate_validation_summary(results)
            
            return {
                "data_type": "profile",
                "cycle_number": profile_data.get("cycle_number", "unknown"),
                "validation_results": [self._result_to_dict(r) for r in results],
                "quality_score": quality_score,
                "summary": summary,
                "validation_timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("Profile validation failed", error=str(e), exc_info=True)
            return {
                "data_type": "profile",
                "validation_error": str(e),
                "quality_score": 0.0
            }
    
    async def validate_measurement_data(self, measurement_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate ARGO measurement data.
        
        Args:
            measurement_data: Measurement data dictionary
            
        Returns:
            Dict containing validation results
        """
        try:
            results = []
            
            # Apply measurement validation rules
            for rule in self.validation_rules['measurement']:
                result = self._apply_measurement_rule(rule, measurement_data)
                results.append(result)
            
            # Calculate quality score
            quality_score = self._calculate_validation_score(results)
            
            # Generate summary
            summary = self._generate_validation_summary(results)
            
            return {
                "data_type": "measurement",
                "pressure": measurement_data.get("pressure", "unknown"),
                "validation_results": [self._result_to_dict(r) for r in results],
                "quality_score": quality_score,
                "summary": summary,
                "validation_timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("Measurement validation failed", error=str(e), exc_info=True)
            return {
                "data_type": "measurement",
                "validation_error": str(e),
                "quality_score": 0.0
            }
    
    def _apply_float_rule(self, rule: ValidationRule, data: Dict[str, Any]) -> ValidationResult:
        """Apply a validation rule to float data."""
        
        if rule.name == "wmo_id_format":
            wmo_id = data.get("wmo_id", "")
            if not wmo_id:
                return ValidationResult(rule, False, "WMO ID is missing")
            
            # Check if WMO ID is 7-10 digit number
            if re.match(r'^\d{7,10}$', str(wmo_id)):
                return ValidationResult(rule, True, "WMO ID format is valid", wmo_id)
            else:
                return ValidationResult(rule, False, f"WMO ID format invalid: {wmo_id}", wmo_id, "7-10 digits")
        
        elif rule.name == "platform_number_present":
            platform_number = data.get("platform_number", "")
            if platform_number:
                return ValidationResult(rule, True, "Platform number is present", platform_number)
            else:
                return ValidationResult(rule, False, "Platform number is missing")
        
        elif rule.name == "float_type_valid":
            float_type = data.get("float_type", "")
            valid_types = ["APEX", "SOLO", "ARVOR", "PROVOR", "NOVA", "NEMO", ""]
            if not float_type or float_type.upper() in valid_types:
                return ValidationResult(rule, True, "Float type is valid", float_type)
            else:
                return ValidationResult(rule, False, f"Unknown float type: {float_type}", float_type, valid_types)
        
        elif rule.name == "deployment_location_valid":
            lat = data.get("deployment_latitude")
            lon = data.get("deployment_longitude")
            
            if lat is None or lon is None:
                return ValidationResult(rule, True, "Deployment location not provided (optional)")
            
            # Check coordinate ranges
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                # Additional check: should be over ocean (simplified check)
                if self._is_likely_ocean_location(lat, lon):
                    return ValidationResult(rule, True, "Deployment location is valid", f"{lat}, {lon}")
                else:
                    return ValidationResult(rule, False, f"Deployment location may be on land: {lat}, {lon}", f"{lat}, {lon}")
            else:
                return ValidationResult(rule, False, f"Deployment coordinates out of range: {lat}, {lon}", f"{lat}, {lon}")
        
        else:
            return ValidationResult(rule, True, f"Rule {rule.name} not implemented")
    
    def _apply_profile_rule(self, rule: ValidationRule, data: Dict[str, Any]) -> ValidationResult:
        """Apply a validation rule to profile data."""
        
        if rule.name == "latitude_range":
            lat = data.get("latitude")
            if lat is None:
                return ValidationResult(rule, False, "Latitude is missing")
            
            if -90 <= lat <= 90:
                return ValidationResult(rule, True, "Latitude is within valid range", lat)
            else:
                return ValidationResult(rule, False, f"Latitude out of range: {lat}", lat, "[-90, 90]")
        
        elif rule.name == "longitude_range":
            lon = data.get("longitude")
            if lon is None:
                return ValidationResult(rule, False, "Longitude is missing")
            
            if -180 <= lon <= 180:
                return ValidationResult(rule, True, "Longitude is within valid range", lon)
            else:
                return ValidationResult(rule, False, f"Longitude out of range: {lon}", lon, "[-180, 180]")
        
        elif rule.name == "profile_date_reasonable":
            profile_date = data.get("profile_date")
            if profile_date is None:
                return ValidationResult(rule, False, "Profile date is missing")
            
            # Convert to date if it's a string
            if isinstance(profile_date, str):
                try:
                    profile_date = datetime.strptime(profile_date, "%Y-%m-%d").date()
                except:
                    return ValidationResult(rule, False, f"Invalid date format: {profile_date}")
            
            # Check reasonable date range (after 1990, not future)
            min_date = date(1990, 1, 1)
            max_date = date.today()
            
            if min_date <= profile_date <= max_date:
                return ValidationResult(rule, True, "Profile date is reasonable", profile_date)
            else:
                return ValidationResult(rule, False, f"Profile date unreasonable: {profile_date}", profile_date, f"[{min_date}, {max_date}]")
        
        elif rule.name == "cycle_number_positive":
            cycle_number = data.get("cycle_number")
            if cycle_number is None:
                return ValidationResult(rule, False, "Cycle number is missing")
            
            if isinstance(cycle_number, int) and cycle_number > 0:
                return ValidationResult(rule, True, "Cycle number is positive", cycle_number)
            else:
                return ValidationResult(rule, False, f"Cycle number invalid: {cycle_number}", cycle_number, "positive integer")
        
        elif rule.name == "location_over_ocean":
            lat = data.get("latitude")
            lon = data.get("longitude")
            
            if lat is None or lon is None:
                return ValidationResult(rule, False, "Location coordinates missing")
            
            if self._is_likely_ocean_location(lat, lon):
                return ValidationResult(rule, True, "Location appears to be over ocean", f"{lat}, {lon}")
            else:
                return ValidationResult(rule, False, f"Location may be over land: {lat}, {lon}", f"{lat}, {lon}")
        
        elif rule.name == "temperature_range_reasonable":
            min_temp = data.get("min_temperature")
            max_temp = data.get("max_temperature")
            
            if min_temp is None and max_temp is None:
                return ValidationResult(rule, True, "No temperature data to validate")
            
            # Ocean temperature range check
            temp_issues = []
            if min_temp is not None and (min_temp < -3 or min_temp > 40):
                temp_issues.append(f"min_temp: {min_temp}")
            if max_temp is not None and (max_temp < -3 or max_temp > 40):
                temp_issues.append(f"max_temp: {max_temp}")
            
            if temp_issues:
                return ValidationResult(rule, False, f"Temperature out of ocean range: {', '.join(temp_issues)}")
            else:
                return ValidationResult(rule, True, "Temperature range is reasonable")
        
        elif rule.name == "salinity_range_reasonable":
            min_sal = data.get("min_salinity")
            max_sal = data.get("max_salinity")
            
            if min_sal is None and max_sal is None:
                return ValidationResult(rule, True, "No salinity data to validate")
            
            # Ocean salinity range check
            sal_issues = []
            if min_sal is not None and (min_sal < 0 or min_sal > 50):
                sal_issues.append(f"min_salinity: {min_sal}")
            if max_sal is not None and (max_sal < 0 or max_sal > 50):
                sal_issues.append(f"max_salinity: {max_sal}")
            
            if sal_issues:
                return ValidationResult(rule, False, f"Salinity out of ocean range: {', '.join(sal_issues)}")
            else:
                return ValidationResult(rule, True, "Salinity range is reasonable")
        
        else:
            return ValidationResult(rule, True, f"Rule {rule.name} not implemented")
    
    def _apply_measurement_rule(self, rule: ValidationRule, data: Dict[str, Any]) -> ValidationResult:
        """Apply a validation rule to measurement data."""
        
        if rule.name == "pressure_positive":
            pressure = data.get("pressure")
            if pressure is None:
                return ValidationResult(rule, False, "Pressure is missing")
            
            if pressure > 0:
                return ValidationResult(rule, True, "Pressure is positive", pressure)
            else:
                return ValidationResult(rule, False, f"Pressure not positive: {pressure}", pressure)
        
        elif rule.name == "temperature_ocean_range":
            temperature = data.get("temperature")
            if temperature is None:
                return ValidationResult(rule, True, "No temperature data to validate")
            
            if -2 <= temperature <= 40:
                return ValidationResult(rule, True, "Temperature within ocean range", temperature)
            else:
                return ValidationResult(rule, False, f"Temperature out of ocean range: {temperature}", temperature, "[-2, 40]°C")
        
        elif rule.name == "salinity_ocean_range":
            salinity = data.get("salinity")
            if salinity is None:
                return ValidationResult(rule, True, "No salinity data to validate")
            
            if 0 <= salinity <= 50:
                return ValidationResult(rule, True, "Salinity within ocean range", salinity)
            else:
                return ValidationResult(rule, False, f"Salinity out of ocean range: {salinity}", salinity, "[0, 50] PSU")
        
        elif rule.name == "oxygen_positive":
            oxygen = data.get("oxygen")
            if oxygen is None:
                return ValidationResult(rule, True, "No oxygen data to validate")
            
            if oxygen > 0:
                return ValidationResult(rule, True, "Oxygen concentration is positive", oxygen)
            else:
                return ValidationResult(rule, False, f"Oxygen concentration not positive: {oxygen}", oxygen)
        
        elif rule.name == "quality_flag_valid":
            # Check all quality flags
            qf_fields = ["pressure_qf", "temperature_qf", "salinity_qf", "oxygen_qf"]
            valid_flags = ["1", "2", "3", "4", "5", "8", "9"]
            
            invalid_flags = []
            for field in qf_fields:
                qf_value = data.get(field)
                if qf_value is not None and str(qf_value) not in valid_flags:
                    invalid_flags.append(f"{field}: {qf_value}")
            
            if invalid_flags:
                return ValidationResult(rule, False, f"Invalid quality flags: {', '.join(invalid_flags)}")
            else:
                return ValidationResult(rule, True, "Quality flags are valid")
        
        else:
            return ValidationResult(rule, True, f"Rule {rule.name} not implemented")
    
    def _is_likely_ocean_location(self, lat: float, lon: float) -> bool:
        """
        Simple check if coordinates are likely over ocean.
        This is a simplified check - a real implementation would use bathymetry data.
        """
        # Very basic checks for major land masses
        # This is not comprehensive and should be replaced with proper bathymetry data
        
        # Major continental checks (very rough)
        if -20 <= lat <= 70 and -10 <= lon <= 60:  # Europe/Africa
            if 30 <= lat <= 70 and -10 <= lon <= 40:  # Europe
                return False
            if -35 <= lat <= 37 and 15 <= lon <= 55:  # Africa
                return False
        
        if 10 <= lat <= 80 and 60 <= lon <= 180:  # Asia
            return False
        
        if -60 <= lat <= 15 and -85 <= lon <= -30:  # South America
            return False
        
        if 15 <= lat <= 85 and -170 <= lon <= -50:  # North America
            return False
        
        # Default to ocean (this is very rough)
        return True
    
    def _calculate_validation_score(self, results: List[ValidationResult]) -> float:
        """Calculate overall validation quality score (0-100)."""
        if not results:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        # Weight by severity
        severity_weights = {
            'error': 1.0,
            'warning': 0.7,
            'info': 0.3
        }
        
        for result in results:
            weight = severity_weights.get(result.rule.severity, 0.5)
            score = 100.0 if result.passed else 0.0
            
            total_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            return total_score / total_weight
        else:
            return 0.0
    
    def _generate_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate validation summary statistics."""
        total_rules = len(results)
        passed_rules = sum(1 for r in results if r.passed)
        failed_rules = total_rules - passed_rules
        
        # Count by severity
        errors = sum(1 for r in results if not r.passed and r.rule.severity == 'error')
        warnings = sum(1 for r in results if not r.passed and r.rule.severity == 'warning')
        info_issues = sum(1 for r in results if not r.passed and r.rule.severity == 'info')
        
        # Count by category
        categories = {}
        for result in results:
            category = result.rule.category
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0, "failed": 0}
            
            categories[category]["total"] += 1
            if result.passed:
                categories[category]["passed"] += 1
            else:
                categories[category]["failed"] += 1
        
        return {
            "total_rules": total_rules,
            "passed_rules": passed_rules,
            "failed_rules": failed_rules,
            "pass_rate": (passed_rules / total_rules * 100) if total_rules > 0 else 0,
            "errors": errors,
            "warnings": warnings,
            "info_issues": info_issues,
            "categories": categories
        }
    
    def _result_to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """Convert ValidationResult to dictionary."""
        return {
            "rule_name": result.rule.name,
            "rule_description": result.rule.description,
            "severity": result.rule.severity,
            "category": result.rule.category,
            "passed": result.passed,
            "message": result.message,
            "value": result.value,
            "expected": result.expected
        }
    
    async def detect_anomalies(self, measurements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect anomalies in measurement data using statistical methods.
        
        Args:
            measurements: List of measurement dictionaries
            
        Returns:
            Dict containing anomaly detection results
        """
        try:
            if not measurements:
                return {"anomalies": [], "anomaly_count": 0}
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(measurements)
            
            anomalies = []
            
            # Temperature anomalies using z-score
            if 'temperature' in df.columns:
                temp_anomalies = self._detect_zscore_anomalies(
                    df, 'temperature', threshold=3.0, name='temperature_outlier'
                )
                anomalies.extend(temp_anomalies)
            
            # Salinity anomalies
            if 'salinity' in df.columns:
                sal_anomalies = self._detect_zscore_anomalies(
                    df, 'salinity', threshold=3.0, name='salinity_outlier'
                )
                anomalies.extend(sal_anomalies)
            
            # Pressure sequence anomalies
            if 'pressure' in df.columns:
                pressure_anomalies = self._detect_pressure_anomalies(df)
                anomalies.extend(pressure_anomalies)
            
            return {
                "anomalies": anomalies,
                "anomaly_count": len(anomalies),
                "total_measurements": len(measurements),
                "anomaly_rate": len(anomalies) / len(measurements) if measurements else 0
            }
            
        except Exception as e:
            logger.error("Anomaly detection failed", error=str(e), exc_info=True)
            return {"error": str(e), "anomaly_count": 0}
    
    def _detect_zscore_anomalies(
        self, 
        df: pd.DataFrame, 
        column: str, 
        threshold: float = 3.0,
        name: str = "outlier"
    ) -> List[Dict[str, Any]]:
        """Detect anomalies using z-score method."""
        anomalies = []
        
        if column not in df.columns or df[column].isna().all():
            return anomalies
        
        # Calculate z-scores
        mean_val = df[column].mean()
        std_val = df[column].std()
        
        if std_val == 0:
            return anomalies  # No variation
        
        z_scores = np.abs((df[column] - mean_val) / std_val)
        outlier_indices = z_scores > threshold
        
        for idx in df[outlier_indices].index:
            anomalies.append({
                "type": name,
                "measurement_index": int(idx),
                "value": float(df.loc[idx, column]),
                "z_score": float(z_scores.loc[idx]),
                "mean": float(mean_val),
                "std": float(std_val),
                "threshold": threshold
            })
        
        return anomalies
    
    def _detect_pressure_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect pressure sequence anomalies."""
        anomalies = []
        
        if 'pressure' not in df.columns or len(df) < 2:
            return anomalies
        
        # Sort by pressure to check sequence
        df_sorted = df.sort_values('pressure')
        pressure_values = df_sorted['pressure'].values
        
        # Check for large gaps or reversals
        pressure_diffs = np.diff(pressure_values)
        
        # Detect large jumps (more than 100 dbar)
        large_jumps = np.where(pressure_diffs > 100)[0]
        for idx in large_jumps:
            anomalies.append({
                "type": "pressure_large_jump",
                "measurement_index": int(idx),
                "pressure_before": float(pressure_values[idx]),
                "pressure_after": float(pressure_values[idx + 1]),
                "jump_size": float(pressure_diffs[idx])
            })
        
        # Detect negative pressure differences (should be rare)
        negative_diffs = np.where(pressure_diffs < -50)[0]  # Allow small variations
        for idx in negative_diffs:
            anomalies.append({
                "type": "pressure_reversal",
                "measurement_index": int(idx),
                "pressure_before": float(pressure_values[idx]),
                "pressure_after": float(pressure_values[idx + 1]),
                "reversal_size": float(pressure_diffs[idx])
            })
        
        return anomalies
