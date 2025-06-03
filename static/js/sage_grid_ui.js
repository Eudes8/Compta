/**
 * Sage Grid UI - Keyboard navigation and validation for the Sage-like grid interface
 */
class SageGridUI {
    constructor(config) {
        this.gridElement = document.getElementById('sageGrid');
        this.api = config.api;
        this.grid = config.grid;

        // Elements UI
        this.lookups = {
            compte: document.getElementById('compteLookup'),
            tiers: document.getElementById('tiersLookup')
        };
        this.calculator = document.getElementById('calculatorPanel');
        this.activeCell = null;
        this.activeInput = null;

        // État
        this.currentJournal = null;
        this.lookupVisible = false;
        this.calculatorVisible = false;

        this.setupEventListeners();
        this.setupKeyboardNavigation();
        this.initializeToolbarButtons(); // Initialiser les boutons de la barre d'outils
    }

    setupEventListeners() {
        // Navigation dans la grille
        this.gridElement.addEventListener('click', this.handleGridClick.bind(this));
        
        // Gestion des lookups
        this.gridElement.addEventListener('focusin', this.handleFocusIn.bind(this));
        document.addEventListener('click', this.handleDocumentClick.bind(this));
        
        // Calculatrice
        document.getElementById('btnCalc').addEventListener('click', this.toggleCalculator.bind(this));
        this.calculator.addEventListener('click', this.handleCalculatorClick.bind(this));
        
        // Boutons d'action
        document.getElementById('btnNewPiece').addEventListener('click', () => this.grid.newPiece());
        document.getElementById('btnSave').addEventListener('click', () => this.grid.savePiece());
        document.getElementById('btnDelete').addEventListener('click', () => this.grid.deletePiece());
        document.getElementById('btnBalance').addEventListener('click', () => this.grid.autoBalance());
        
        // Gestion de la saisie des montants
        this.gridElement.addEventListener('input', (e) => {
            const input = e.target;
            if (input.dataset.column === 'debit' || input.dataset.column === 'credit') {
                this.handleAmountInput(input);
            }
        });

        // Gestion de la recherche de comptes
        this.gridElement.addEventListener('input', (e) => {
            const input = e.target;
            if (input.classList.contains('account-search')) {
                const query = input.value;
                if (query.length >= 2) {
                    this.showLookup('compte', query);
                }
            } else if (input.classList.contains('tiers-search')) {
                const query = input.value;
                if (query.length >= 2) {
                    this.showLookup('tiers', query);
                }
            }
        });

        // Focus et sélection automatique des inputs
        this.gridElement.addEventListener('focus', (e) => {
            const input = e.target;
            if (input.tagName === 'INPUT') {
                input.select();
                this.activeInput = input;
                this.activeCell = input.closest('td');
            }
        }, true);

        // Événements pour les lookups
        const lookupInputs = document.querySelectorAll('.sage-i7-search-input');
        lookupInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                const query = e.target.value;
                const type = e.target.closest('.sage-i7-search-popup').id.replace('SearchTemplate', '');
                if (query.length >= 2) {
                    this.performLookupSearch(type, query);
                }
            });
        });

        // Ajouter la navigation au clavier
        this.grid.addEventListener('keydown', (e) => this.handleKeyboardNavigation(e));
        
        // Gérer la mise à jour automatique des totaux lors de la saisie
        this.grid.addEventListener('input', (e) => {
            if (e.target.matches('input[type="number"]')) {
                this.updateTotals();
            }
        });
    }

    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Ne pas intercepter les raccourcis si une boîte de dialogue est ouverte
            if (this.lookupVisible || this.calculatorVisible) {
                if (e.key === 'Escape') {
                    this.hideLookups();
                    this.hideCalculator();
                }
                return;
            }
            
            // Navigation et actions
            if (this.activeInput) {
                switch(e.key) {
                    case 'Tab':
                        if (!e.shiftKey) {
                            e.preventDefault();
                            this.moveToCell('right');
                        }
                        break;
                    case 'Enter':
                        e.preventDefault();
                        this.moveToCell('down');
                        break;
                    case 'ArrowDown':
                        e.preventDefault();
                        this.moveToCell('down');
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        this.moveToCell('up');
                        break;
                    case 'F2':
                        e.preventDefault();
                        this.toggleCalculator();
                        break;
                    case 'F4':
                        e.preventDefault();
                        const column = this.activeInput.dataset.column;
                        if (column === 'compte' || column === 'tiers') {
                            this.showLookup(column);
                        }
                        break;
                }
            }
            
            // Raccourcis globaux
            switch(e.key) {
                case 'F9':
                    e.preventDefault();
                    this.toggleCalculator();
                    break;
                case 'F8':
                    e.preventDefault();
                    this.grid.autoBalance();
                    break;
                case 'F6':
                    e.preventDefault();
                    this.grid.savePiece();
                    break;
            }
            
            // Recherche avec F4
            if (e.key === 'F4' && this.activeInput) {
                e.preventDefault();
                const column = this.activeInput.dataset.column;
                if (column === 'compte' || column === 'tiers') {
                    this.showLookup(column);
                }
            }
        });
    }

    // Actions des boutons
    initializeToolbarButtons() {
        // Boutons d'actions principales
        document.getElementById('btnAdd').addEventListener('click', () => this.newPiece());
        document.getElementById('btnView').addEventListener('click', () => this.viewPiece());
        document.getElementById('btnEdit').addEventListener('click', () => this.editPiece());
        document.getElementById('btnDelete').addEventListener('click', () => this.deletePiece());
        
        // Boutons de navigation
        document.getElementById('btnPrev').addEventListener('click', () => this.navigatePiece('prev'));
        document.getElementById('btnNext').addEventListener('click', () => this.navigatePiece('next'));
        document.getElementById('btnSearch').addEventListener('click', () => this.searchPiece());
        document.getElementById('btnGoto').addEventListener('click', () => this.gotoPiece());
        
        // Boutons d'outils
        document.getElementById('btnInverse').addEventListener('click', () => this.inversePiece());
        document.getElementById('btnCalc').addEventListener('click', () => this.toggleCalculator());
        document.getElementById('btnSort').addEventListener('click', () => this.sortPiece());
        
        // Boutons de validation
        document.getElementById('btnBalance').addEventListener('click', () => this.grid.autoBalance());
        document.getElementById('btnValidate').addEventListener('click', () => this.validatePiece());
    }

    // Nouvelle pièce
    newPiece() {
        if (this.grid.modified) {
            if (!confirm('Des modifications non sauvegardées seront perdues. Continuer ?')) {
                return;
            }
        }
        this.grid.initializeGrid();
        this.setStatusMessage('Nouvelle pièce');
    }

    // Consulter une pièce
    viewPiece() {
        const pieceNumber = prompt('Entrez le numéro de pièce à consulter :');
        if (!pieceNumber) return;

        this.api.getPieceData(pieceNumber)
            .then(data => {
                if (data.success) {
                    this.loadPieceData(data.piece, true); // true = mode consultation
                    this.setStatusMessage('Consultation de la pièce ' + pieceNumber);
                } else {
                    alert('Pièce non trouvée');
                }
            })
            .catch(error => {
                console.error('Erreur lors de la consultation:', error);
                alert('Erreur lors de la consultation de la pièce');
            });
    }

    // Modifier une pièce
    editPiece() {
        const pieceNumber = prompt('Entrez le numéro de pièce à modifier :');
        if (!pieceNumber) return;

        this.api.getPieceData(pieceNumber)
            .then(data => {
                if (data.success) {
                    this.loadPieceData(data.piece, false); // false = mode édition
                    this.setStatusMessage('Modification de la pièce ' + pieceNumber);
                } else {
                    alert('Pièce non trouvée');
                }
            })
            .catch(error => {
                console.error('Erreur lors de la modification:', error);
                alert('Erreur lors de la modification de la pièce');
            });
    }

    // Supprimer une pièce
    deletePiece() {
        const pieceNumber = prompt('Entrez le numéro de pièce à supprimer :');
        if (!pieceNumber) return;

        if (confirm('Êtes-vous sûr de vouloir supprimer la pièce ' + pieceNumber + ' ?')) {
            this.api.deletePiece(pieceNumber)
                .then(response => {
                    if (response.success) {
                        this.setStatusMessage('Pièce ' + pieceNumber + ' supprimée');
                        this.grid.initializeGrid();
                    } else {
                        alert('Erreur lors de la suppression : ' + response.message);
                    }
                })
                .catch(error => {
                    console.error('Erreur lors de la suppression:', error);
                    alert('Erreur lors de la suppression de la pièce');
                });
        }
    }

    // Navigation entre les pièces
    navigatePiece(direction) {
        const currentPiece = document.getElementById('pieceNumber').value;
        this.api.getAdjacentPiece(currentPiece, direction)
            .then(data => {
                if (data.success && data.piece) {
                    this.loadPieceData(data.piece, true);
                    this.setStatusMessage(`Pièce ${direction === 'prev' ? 'précédente' : 'suivante'}`);
                } else {
                    alert(`Pas de pièce ${direction === 'prev' ? 'précédente' : 'suivante'}`);
                }
            })
            .catch(error => {
                console.error('Erreur de navigation:', error);
                alert('Erreur lors de la navigation');
            });
    }

    // Rechercher une pièce
    searchPiece() {
        const searchForm = document.createElement('div');
        searchForm.innerHTML = `
            <div class="sage-i7-search-form">
                <h3>Recherche de pièce</h3>
                <div>
                    <label>Numéro de pièce:</label>
                    <input type="text" id="searchPieceNumber">
                </div>
                <div>
                    <label>Date début:</label>
                    <input type="date" id="searchDateStart">
                </div>
                <div>
                    <label>Date fin:</label>
                    <input type="date" id="searchDateEnd">
                </div>
                <div>
                    <label>Montant:</label>
                    <input type="text" id="searchAmount">
                </div>
                <div>
                    <button id="btnSearchSubmit">Rechercher</button>
                    <button id="btnSearchCancel">Annuler</button>
                </div>
            </div>
        `;

        document.body.appendChild(searchForm);
        
        // Gérer la recherche...
        document.getElementById('btnSearchSubmit').addEventListener('click', () => {
            const criteria = {
                pieceNumber: document.getElementById('searchPieceNumber').value,
                dateStart: document.getElementById('searchDateStart').value,
                dateEnd: document.getElementById('searchDateEnd').value,
                amount: document.getElementById('searchAmount').value
            };

            this.api.searchPieces(criteria)
                .then(results => {
                    // Afficher les résultats...
                });
        });
    }

    // Aller à une pièce spécifique
    gotoPiece() {
        const pieceNumber = prompt('Entrez le numéro de pièce :');
        if (pieceNumber) {
            this.api.getPieceData(pieceNumber)
                .then(data => {
                    if (data.success) {
                        this.loadPieceData(data.piece, true);
                    } else {
                        alert('Pièce non trouvée');
                    }
                });
        }
    }

    // Inverser débit/crédit
    inversePiece() {
        const rows = this.gridElement.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const debitInput = row.querySelector('[data-column="debit"]');
            const creditInput = row.querySelector('[data-column="credit"]');
            
            if (debitInput && creditInput) {
                const debitValue = this.parseAmount(debitInput.value);
                const creditValue = this.parseAmount(creditInput.value);
                
                debitInput.value = this.formatAmount(creditValue);
                creditInput.value = this.formatAmount(debitValue);
            }
        });
        
        this.calculateTotals();
        this.setStatusMessage('Montants inversés');
    }

    // Trier les lignes
    sortPiece() {
        const tbody = this.gridElement.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const compteA = a.querySelector('[data-column="compte"]').value;
            const compteB = b.querySelector('[data-column="compte"]').value;
            return compteA.localeCompare(compteB);
        });
        
        // Vider et reremplir le tbody avec les lignes triées
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
        
        this.setStatusMessage('Lignes triées par numéro de compte');
    }

    // Valider la pièce
    validatePiece() {
        if (!this.validatePieceData()) {
            return;
        }

        const pieceData = this.grid.getPieceData();
        this.api.savePiece(pieceData)
            .then(response => {
                if (response.success) {
                    this.setStatusMessage('Pièce enregistrée avec succès');
                    this.grid.modified = false;
                    
                    // Proposer une nouvelle pièce
                    if (confirm('Pièce enregistrée. Créer une nouvelle pièce ?')) {
                        this.newPiece();
                    }
                } else {
                    alert('Erreur lors de l\'enregistrement : ' + response.message);
                }
            })
            .catch(error => {
                console.error('Erreur de validation:', error);
                alert('Erreur lors de la validation de la pièce');
            });
    }

    // Validation des données de la pièce
    validatePieceData() {
        // Vérifier les champs obligatoires
        const pieceNumber = document.getElementById('pieceNumber').value;
        const pieceDate = document.getElementById('pieceDate').value;
        
        if (!pieceNumber) {
            alert('Le numéro de pièce est obligatoire');
            return false;
        }
        
        if (!pieceDate) {
            alert('La date de pièce est obligatoire');
            return false;
        }
        
        // Vérifier l'équilibre
        const { totalDebit, totalCredit } = this.calculateTotals();
        if (Math.abs(totalDebit - totalCredit) > 0.01) {
            alert('La pièce n\'est pas équilibrée');
            return false;
        }
        
        // Vérifier qu'il y a au moins une ligne
        const lines = this.grid.getPieceData().lines;
        if (lines.length === 0) {
            alert('La pièce doit contenir au moins une ligne');
            return false;
        }
        
        return true;
    }

    // Charger les données d'une pièce
    loadPieceData(piece, readOnly = false) {
        // Remplir l'en-tête
        document.getElementById('pieceNumber').value = piece.numero;
        document.getElementById('pieceDate').value = piece.date;
        document.getElementById('pieceRef').value = piece.reference || '';
        
        // Vider la grille
        this.grid.clearGrid();
        
        // Remplir les lignes
        piece.lines.forEach(line => {
            const row = this.grid.addNewLine();
            
            const inputs = row.querySelectorAll('input');
            inputs.forEach(input => {
                input.readOnly = readOnly;
                
                switch(input.dataset.column) {
                    case 'compte':
                        input.value = line.compte;
                        break;
                    case 'libelle':
                        input.value = line.libelle;
                        break;
                    case 'debit':
                        input.value = this.formatAmount(line.debit);
                        break;
                    case 'credit':
                        input.value = this.formatAmount(line.credit);
                        break;
                    case 'echeance':
                        input.value = line.echeance || '';
                        break;
                    case 'tiers':
                        input.value = line.tiers || '';
                        break;
                }
            });
        });
        
        this.calculateTotals();
    }    // Mettre à jour le message de statut
    setStatusMessage(message) {
        const statusElement = document.getElementById('statusMessage');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.style.opacity = '1';
            
            // Faire disparaître le message après 3 secondes
            setTimeout(() => {
                statusElement.style.opacity = '0';
            }, 3000);
        }
    }

    // Gestion des saisies de montants
    handleAmountInput(input) {
        // Formater le montant
        let value = input.value.replace(/[^0-9.,]/g, '');
        value = value.replace(',', '.');
        const amount = parseFloat(value);

        if (!isNaN(amount)) {
            // Si on saisit un montant au débit, vider le crédit et vice versa
            const row = input.closest('tr');
            const isDebit = input.dataset.column === 'debit';
            const otherInput = row.querySelector(`[data-column="${isDebit ? 'credit' : 'debit'}"]`);
            
            if (amount > 0) {
                otherInput.value = '';
            }

            // Formater le montant avec 2 décimales
            input.value = this.formatAmount(amount);
        }

        // Calculer les totaux
        this.calculateTotals();
        this.grid.markAsModified();
    }

    // Formater un montant
    formatAmount(amount) {
        return new Intl.NumberFormat('fr-FR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount || 0);
    }

    // Parser un montant depuis une chaîne
    parseAmount(value) {
        if (!value) return 0;
        // Enlever les espaces et remplacer la virgule par un point
        const cleanValue = value.replace(/\s/g, '').replace(',', '.');
        const parsed = parseFloat(cleanValue);
        return isNaN(parsed) ? 0 : parsed;
    }

    // Valider une ligne d'écriture
    validateLine(row) {
        const compte = row.querySelector('input[data-column="compte"]').value;
        const debit = this.parseAmount(row.querySelector('input[data-column="debit"]').value);
        const credit = this.parseAmount(row.querySelector('input[data-column="credit"]').value);
        const libelle = row.querySelector('input[data-column="libelle"]').value;

        let errors = [];
        
        if (!compte) {
            errors.push('Le numéro de compte est obligatoire');
        }
        
        if (debit > 0 && credit > 0) {
            errors.push('Une ligne ne peut pas avoir à la fois un débit et un crédit');
        }
        
        if (debit === 0 && credit === 0) {
            errors.push('Le montant doit être différent de zéro');
        }
        
        if (!libelle.trim()) {
            errors.push('Le libellé est obligatoire');
        }

        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    // Valider l'ensemble de la pièce
    validatePiece() {
        let totalDebit = 0;
        let totalCredit = 0;
        let isValid = true;
        let errorMessages = [];

        const rows = this.grid.querySelectorAll('tr:not(:first-child)');
        rows.forEach((row, index) => {
            const validation = this.validateLine(row);
            if (!validation.isValid) {
                isValid = false;
                errorMessages.push(`Ligne ${index + 1}: ${validation.errors.join(', ')}`);
            }

            totalDebit += this.parseAmount(row.querySelector('input[data-column="debit"]').value);
            totalCredit += this.parseAmount(row.querySelector('input[data-column="credit"]').value);
        });

        // Vérifier l'équilibre débit/crédit
        if (Math.abs(totalDebit - totalCredit) > 0.01) {
            isValid = false;
            errorMessages.push('La pièce n\'est pas équilibrée');
        }

        return {
            isValid: isValid,
            errors: errorMessages,
            totalDebit: totalDebit,
            totalCredit: totalCredit
        };
    }

    addNewRow() {
        const template = document.getElementById('newLineTemplate');
        if (!template) return;

        const newRow = template.content.cloneNode(true);
        this.grid.querySelector('tbody').appendChild(newRow);
        
        // Focus sur le premier champ de la nouvelle ligne
        const firstInput = newRow.querySelector('input');
        if (firstInput) firstInput.focus();
        
        this.updateTotals();
    }

    deleteRow(row) {
        if (this.grid.querySelectorAll('tr:not(:first-child)').length > 1) {
            row.remove();
            this.updateTotals();
        } else {
            // Vider la dernière ligne au lieu de la supprimer
            const inputs = row.querySelectorAll('input');
            inputs.forEach(input => input.value = '');
        }
    }
    
    updateTotals() {
        let totalDebit = 0;
        let totalCredit = 0;
        
        // Calculer les totaux
        const rows = this.grid.querySelectorAll('tr:not(:first-child)');
        rows.forEach(row => {
            const debitInput = row.querySelector('input[data-column="debit"]');
            const creditInput = row.querySelector('input[data-column="credit"]');
            
            if (debitInput) totalDebit += this.parseAmount(debitInput.value);
            if (creditInput) totalCredit += this.parseAmount(creditInput.value);
        });
        
        // Mettre à jour les totaux affichés
        document.getElementById('totalDebit').textContent = this.formatAmount(totalDebit);
        document.getElementById('totalCredit').textContent = this.formatAmount(totalCredit);
        
        // Calculer et afficher le solde
        const balance = totalDebit - totalCredit;
        const balanceElement = document.getElementById('balance');
        if (balanceElement) {
            balanceElement.textContent = this.formatAmount(Math.abs(balance));
            balanceElement.classList.toggle('negative', balance < 0);
        }
    }

    // Gestion du focus et de la navigation
    handleGridClick(e) {
        const cell = e.target.closest('td');
        if (cell) {
            const input = cell.querySelector('input');
            if (input) {
                input.focus();
                input.select();
                this.activeCell = cell;
                this.activeInput = input;
            }
        }
    }

    // Navigation dans la grille
    moveToCell(direction) {
        if (!this.activeCell) return;

        const currentRow = this.activeCell.parentElement;
        const currentIndex = Array.from(currentRow.children).indexOf(this.activeCell);
        let targetInput = null;

        switch (direction) {
            case 'right':
                // Passer à la cellule suivante ou première cellule de la ligne suivante
                const nextCell = this.activeCell.nextElementSibling;
                if (nextCell) {
                    targetInput = nextCell.querySelector('input');
                } else {
                    const nextRow = currentRow.nextElementSibling;
                    if (nextRow) {
                        targetInput = nextRow.querySelector('input');
                    }
                }
                break;

            case 'left':
                // Passer à la cellule précédente
                const prevCell = this.activeCell.previousElementSibling;
                if (prevCell) {
                    targetInput = prevCell.querySelector('input');
                }
                break;

            case 'up':
                // Passer à la même cellule de la ligne précédente
                const prevRow = currentRow.previousElementSibling;
                if (prevRow) {
                    targetInput = prevRow.children[currentIndex].querySelector('input');
                }
                break;

            case 'down':
                // Passer à la même cellule de la ligne suivante
                const nextRow = currentRow.nextElementSibling;
                if (nextRow) {
                    targetInput = nextRow.children[currentIndex].querySelector('input');
                }
                break;
        }

        if (targetInput) {
            targetInput.focus();
            targetInput.select();
            this.activeCell = targetInput.closest('td');
            this.activeInput = targetInput;
        }
    }

    // Gérer la navigation au clavier dans la grille
    handleKeyboardNavigation(event) {
        const activeElement = document.activeElement;
        const currentCell = activeElement.closest('td');
        if (!currentCell) return;

        const currentRow = currentCell.parentElement;
        const allCells = Array.from(currentRow.cells);
        const currentIndex = allCells.indexOf(currentCell);
        const allRows = Array.from(this.grid.querySelectorAll('tr'));
        const currentRowIndex = allRows.indexOf(currentRow);

        switch (event.key) {
            case 'Enter':
            case 'ArrowDown':
                event.preventDefault();
                // Aller à la ligne suivante
                if (currentRowIndex < allRows.length - 1) {
                    const nextRow = allRows[currentRowIndex + 1];
                    const nextCell = nextRow.cells[currentIndex];
                    const input = nextCell.querySelector('input');
                    if (input) input.focus();
                } else {
                    // Ajouter une nouvelle ligne si on est sur la dernière
                    this.addNewRow();
                }
                break;

            case 'ArrowUp':
                event.preventDefault();
                // Aller à la ligne précédente
                if (currentRowIndex > 1) { // Skip header row
                    const prevRow = allRows[currentRowIndex - 1];
                    const prevCell = prevRow.cells[currentIndex];
                    const input = prevCell.querySelector('input');
                    if (input) input.focus();
                }
                break;

            case 'ArrowRight':
                // Aller à la cellule suivante
                if (currentIndex < allCells.length - 1) {
                    const nextCell = allCells[currentIndex + 1];
                    const input = nextCell.querySelector('input');
                    if (input) input.focus();
                }
                break;

            case 'ArrowLeft':
                // Aller à la cellule précédente
                if (currentIndex > 0) {
                    const prevCell = allCells[currentIndex - 1];
                    const input = prevCell.querySelector('input');
                    if (input) input.focus();
                }
                break;

            case 'Tab':
                // Laisser le comportement par défaut de Tab
                break;

            case 'Delete':
                if (event.ctrlKey) {
                    event.preventDefault();
                    this.deleteRow(currentRow);
                }
                break;
        }
    }
}
