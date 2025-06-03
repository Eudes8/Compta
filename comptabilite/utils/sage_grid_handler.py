"""
Sage Grid Handler - Utility for handling accounting grid operations

This module provides utility functions to interact with the Sage-like grid interface for
accounting entries. It handles grid data validation, formatting, and computation.
"""
from typing import Dict, List, Optional, Union, Tuple, Any
from decimal import Decimal
import re
import json
from datetime import datetime, date

from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

from comptabilite.models import (
    EcritureComptable, 
    LigneEcriture, 
    JournalComptable, 
    CompteComptablePME,
    Tiers
)


class SageGridHandler:
    """
    Handler for processing and validating Sage-like grid data.
    """
    
    def __init__(self, dossier_pme, journal=None, date_ecriture=None):
        """
        Initialize the grid handler with context.
        
        Args:
            dossier_pme: The DossierPME instance associated with the accounting entry
            journal: Optional JournalComptable instance
            date_ecriture: Optional date for the accounting entry
        """
        self.dossier_pme = dossier_pme
        self.journal = journal
        self.date_ecriture = date_ecriture
        self.errors = []
    
    @staticmethod
    def format_monetary_value(value: Union[str, Decimal, float, int]) -> str:
        """
        Format a monetary value according to French accounting standards.
        
        Args:
            value: The value to format
            
        Returns:
            A formatted string (e.g., "1 234,56")
        """
        if not value and value != 0:
            return ""
            
        # Convert to Decimal for consistent handling
        if isinstance(value, str):
            # Remove any non-numeric characters except decimal separator
            value = value.replace(' ', '').replace(',', '.')
            try:
                value = Decimal(value)
            except:
                return ""
        else:
            value = Decimal(str(value))
            
        # Format with French standards (space as thousands separator, comma as decimal)
        formatted = '{:,.2f}'.format(value).replace(',', ' ').replace('.', ',')
        return formatted
    
    @staticmethod
    def parse_monetary_value(value: str) -> Optional[Decimal]:
        """
        Parse a monetary value from string format to Decimal.
        
        Args:
            value: The string value to parse (e.g., "1 234,56")
            
        Returns:
            Decimal value or None if parsing fails
        """
        if not value:
            return Decimal('0.00')
            
        # Remove spaces and replace comma with dot for decimal
        cleaned = value.replace(' ', '').replace(',', '.')
        try:
            return Decimal(cleaned)
        except:
            return None
    
    @staticmethod
    def validate_account_number(account_number: str, dossier_pme) -> Tuple[bool, Optional[CompteComptablePME]]:
        """
        Validate an account number against the chart of accounts.
        
        Args:
            account_number: The account number to validate
            dossier_pme: The DossierPME instance to check against
            
        Returns:
            Tuple of (is_valid, account_instance)
        """
        if not account_number:
            return False, None
            
        # Clean the account number
        account_number = account_number.strip()
        
        # Try to find the account
        try:
            account = CompteComptablePME.objects.get(
                dossier_pme=dossier_pme,
                numero_compte=account_number,
                est_actif=True,
                nature_compte='DETAIL'
            )
            return True, account
        except CompteComptablePME.DoesNotExist:
            return False, None
    
    @staticmethod
    def validate_tiers_code(tiers_code: str, dossier_pme) -> Tuple[bool, Optional[Tiers]]:
        """
        Validate a tiers (customer/vendor) code.
        
        Args:
            tiers_code: The tiers code to validate
            dossier_pme: The DossierPME instance to check against
            
        Returns:
            Tuple of (is_valid, tiers_instance)
        """
        if not tiers_code:
            return False, None
            
        # Clean the tiers code
        tiers_code = tiers_code.strip().upper()
        
        # Try to find the tiers
        try:
            tiers = Tiers.objects.get(
                dossier_pme=dossier_pme,
                code_tiers=tiers_code,
                est_actif=True
            )
            return True, tiers
        except Tiers.DoesNotExist:
            return False, None
    
    @staticmethod
    def validate_date(date_str: str) -> Optional[date]:
        """
        Validate and parse a date string.
        
        Args:
            date_str: Date string in DD/MM/YY format
            
        Returns:
            Python date object or None if invalid
        """
        if not date_str:
            return None
            
        # Try different date formats
        formats = ["%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
                
        return None
    
    @staticmethod
    def validate_day(day_str: str) -> Optional[int]:
        """
        Validate a day of month.
        
        Args:
            day_str: Day as string
            
        Returns:
            Integer day or None if invalid
        """
        if not day_str:
            return None
            
        try:
            day = int(day_str.strip())
            if 1 <= day <= 31:
                return day
        except ValueError:
            pass
            
        return None
    
    def process_grid_data(self, grid_data: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """
        Process and validate grid data from the frontend.
        
        Args:
            grid_data: List of dictionaries containing grid row data
            
        Returns:
            Tuple of (is_valid, processed_data)
        """
        self.errors = []
        processed_rows = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        
        # Process each row in the grid
        for row_index, row in enumerate(grid_data):
            processed_row = {}
            
            # Skip empty rows
            if all(not value for value in row.values()):
                continue
                
            # Process each field
            for field, value in row.items():
                if field == 'jour':
                    day = self.validate_day(value)
                    if day:
                        processed_row['jour'] = day
                    else:
                        self.errors.append(f"Row {row_index+1}: Invalid day '{value}'")
                
                elif field == 'compte':
                    is_valid, account = self.validate_account_number(value, self.dossier_pme)
                    if is_valid:
                        processed_row['compte_general'] = account
                    else:
                        self.errors.append(f"Row {row_index+1}: Invalid account '{value}'")
                
                elif field == 'tiers':
                    if value:
                        is_valid, tiers = self.validate_tiers_code(value, self.dossier_pme)
                        if is_valid:
                            processed_row['tiers_ligne'] = tiers
                        else:
                            self.errors.append(f"Row {row_index+1}: Invalid tiers code '{value}'")
                
                elif field == 'echeance':
                    if value:
                        parsed_date = self.validate_date(value)
                        if parsed_date:
                            processed_row['date_echeance_ligne'] = parsed_date
                        else:
                            self.errors.append(f"Row {row_index+1}: Invalid date format '{value}'")
                
                elif field == 'debit':
                    if value:
                        debit = self.parse_monetary_value(value)
                        if debit is not None:
                            processed_row['debit'] = debit
                            total_debit += debit
                        else:
                            self.errors.append(f"Row {row_index+1}: Invalid debit amount '{value}'")
                
                elif field == 'credit':
                    if value:
                        credit = self.parse_monetary_value(value)
                        if credit is not None:
                            processed_row['credit'] = credit
                            total_credit += credit
                        else:
                            self.errors.append(f"Row {row_index+1}: Invalid credit amount '{value}'")
                
                else:
                    # Direct mapping for other fields
                    processed_row[field] = value
            
            # Validate account/tiers relationship
            if 'compte_general' in processed_row and processed_row['compte_general'].type_compte in [
                'TIERS_CLIENT', 'TIERS_FOURNISSEUR', 'TIERS_SALARIE'
            ] and 'tiers_ligne' not in processed_row:
                self.errors.append(
                    f"Row {row_index+1}: Tiers code required for account {processed_row['compte_general'].numero_compte}"
                )
            
            # Validate debit/credit rules
            debit = processed_row.get('debit', Decimal('0.00'))
            credit = processed_row.get('credit', Decimal('0.00'))
            
            if debit > 0 and credit > 0:
                self.errors.append(f"Row {row_index+1}: Cannot have both debit and credit values")
            
            if debit == 0 and credit == 0 and 'compte_general' in processed_row:
                self.errors.append(f"Row {row_index+1}: Must specify either debit or credit amount")
            
            processed_rows.append(processed_row)
        
        # Validate overall balance
        balance = total_debit - total_credit
        if balance != 0:
            self.errors.append(
                f"Entry is not balanced. Debit: {self.format_monetary_value(total_debit)}, "
                f"Credit: {self.format_monetary_value(total_credit)}, "
                f"Difference: {self.format_monetary_value(abs(balance))}"
            )
        
        result = {
            'rows': processed_rows,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'balance': balance,
            'is_balanced': balance == 0
        }
        
        return len(self.errors) == 0, result

    @transaction.atomic
    def save_grid_data(self, piece_header: Dict[str, Any], grid_data: List[Dict[str, Any]]) -> Tuple[bool, Union[EcritureComptable, List[str]]]:
        """
        Save validated grid data as an accounting entry.
        
        Args:
            piece_header: Dictionary containing header data for the accounting entry
            grid_data: List of dictionaries containing validated grid row data
            
        Returns:
            Tuple of (success, entry_or_errors)
        """
        is_valid, processed_data = self.process_grid_data(grid_data)
        
        if not is_valid:
            return False, self.errors
        
        # Create the accounting entry header
        try:
            piece_date = piece_header.get('date_ecriture', self.date_ecriture)
            if not piece_date:
                return False, ["Missing entry date"]
                
            entry = EcritureComptable(
                dossier_pme=self.dossier_pme,
                journal=self.journal,
                date_ecriture=piece_date,
                numero_piece=piece_header.get('numero_piece', ''),
                libelle_piece=piece_header.get('libelle_piece', ''),
                numero_facture_liee=piece_header.get('numero_facture', ''),
                reference_piece=piece_header.get('reference', ''),
                date_echeance_piece=piece_header.get('date_echeance', None),
            )
            
            # Add tiers if provided
            if 'tiers_en_tete' in piece_header and piece_header['tiers_en_tete']:
                tiers_code = piece_header['tiers_en_tete']
                is_valid, tiers = self.validate_tiers_code(tiers_code, self.dossier_pme)
                if is_valid:
                    entry.tiers_en_tete = tiers
            
            entry.save()
            
            # Create the accounting entry lines
            for row_data in processed_data['rows']:
                line = LigneEcriture(
                    ecriture=entry,
                    compte_general=row_data['compte_general'],
                    libelle_ligne=row_data.get('libelle', entry.libelle_piece),
                    debit=row_data.get('debit', Decimal('0.00')),
                    credit=row_data.get('credit', Decimal('0.00')),
                )
                
                # Add optional fields if present
                if 'jour' in row_data:
                    line.jour = row_data['jour']
                    
                if 'numero_piece' in row_data:
                    line.numero_piece = row_data['numero_piece']
                    
                if 'numero_facture' in row_data:
                    line.numero_facture = row_data['numero_facture']
                    
                if 'reference' in row_data:
                    line.reference = row_data['reference']
                    
                if 'tiers_ligne' in row_data:
                    line.tiers_ligne = row_data['tiers_ligne']
                    
                if 'date_echeance_ligne' in row_data:
                    line.date_echeance_ligne = row_data['date_echeance_ligne']
                
                line.save()
                
            return True, entry
            
        except Exception as e:
            return False, [str(e)]


def process_sage_grid_data(request, dossier_pme, journal=None, date_ecriture=None):
    """
    Process posted Sage grid data from an AJAX request.
    
    Args:
        request: The Django request object
        dossier_pme: The DossierPME instance
        journal: Optional JournalComptable instance
        date_ecriture: Optional date for the accounting entry
        
    Returns:
        JsonResponse with processing results
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'errors': ['Invalid request method']})
    
    try:
        data = json.loads(request.body)
        header_data = data.get('header', {})
        grid_data = data.get('grid', [])
        
        handler = SageGridHandler(dossier_pme, journal, date_ecriture)
        success, result = handler.save_grid_data(header_data, grid_data)
        
        if success:
            return JsonResponse({
                'success': True,
                'entry_id': result.id,
                'message': _("Entry successfully saved")
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': result
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': ['Invalid JSON data']})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': [str(e)]})


def search_accounts(request, dossier_pme):
    """
    Search for accounts matching a query.
    
    Args:
        request: The Django request object
        dossier_pme: The DossierPME instance
        
    Returns:
        JsonResponse with matching accounts
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': []})
    
    # Search by account number or name
    accounts = CompteComptablePME.objects.filter(
        dossier_pme=dossier_pme,
        est_actif=True,
        nature_compte='DETAIL'
    ).filter(
        Q(numero_compte__icontains=query) | 
        Q(intitule_compte__icontains=query)
    ).order_by('numero_compte')[:20]
    
    results = [{
        'numero': acc.numero_compte,
        'libelle': acc.intitule_compte,
        'type': acc.get_type_compte_display() if acc.type_compte else ""
    } for acc in accounts]
    
    return JsonResponse({'results': results})