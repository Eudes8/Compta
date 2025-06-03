/**
 * Sage Grid - Main functionality
 */
class SageGrid {
    constructor(config) {
        this.api = config.api;
        this.dossierPk = config.dossierPk;
        
        // Interface utilisateur
        this.ui = new SageGridUI({
            grid: this,
            api: this.api
        });
        
        // État
        this.currentJournal = config.initialJournal;
        this.currentPiece = null;
        this.modified = false;
        
        // Elements DOM
        this.elements = {
            journal: document.getElementById('journalSelect'),
            period: document.getElementById('periodSelect'),
            pieceNumber: document.getElementById('pieceNumber'),
            pieceDate: document.getElementById('pieceDate'),
            pieceRef: document.getElementById('pieceRef'),
            totalDebit: document.getElementById('totalDebit'),
            totalCredit: document.getElementById('totalCredit'),
            balance: document.getElementById('balance'),
            status: document.getElementById('statusMessage')
        };
        
        this.setupEventListeners();
        this.initialize();
    }

    initialize() {
        // Initialiser la période avec le mois en cours
        const now = new Date();
        this.elements.period.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        
        // Charger les informations du journal initial
        if (this.currentJournal) {
            this.loadJournalInfo(this.currentJournal);
        }
        
        // Créer une nouvelle pièce
        this.newPiece();
    }

    setupEventListeners() {
        // Changement de journal
        this.elements.journal.addEventListener('change', () => {
            this.currentJournal = this.elements.journal.value;
            this.loadJournalInfo(this.currentJournal);
        });
        
        // Changement de période
        this.elements.period.addEventListener('change', () => {
            if (this.modified) {
                if (confirm('Des modifications non sauvegardées seront perdues. Continuer ?')) {
                    this.newPiece();
                } else {
                    this.elements.period.value = this.currentPeriod;
                }
            } else {
                this.newPiece();
            }
        });
        
        // Numéro de pièce et date
        this.elements.pieceNumber.addEventListener('change', () => this.validatePieceNumber());
        this.elements.pieceDate.addEventListener('change', () => this.validatePieceDate());
    }

    async loadJournalInfo(journalId) {
        try {
            const info = await this.api.getJournalInfo(journalId);
            this.ui.currentJournal = info;
            
            // Suggérer un numéro de pièce
            if (this.elements.pieceNumber.value === '') {
                this.elements.pieceNumber.value = info.derniere_piece || 
                    `${info.type}${new Date().getFullYear().toString().substr(-2)}0001`;
            }
            
        } catch (error) {
            this.showError('Erreur lors du chargement des informations du journal');
        }
    }

    newPiece() {
        // Réinitialiser l'état
        this.currentPiece = {
            journal_pk: this.currentJournal,
            date: new Date().toISOString().split('T')[0],
            piece: '',
            reference: '',
            lignes: []
        };
        
        // Réinitialiser l'interface
        this.elements.pieceDate.value = this.currentPiece.date;
        this.elements.pieceRef.value = '';
        this.clearGrid();
        this.addNewLine();
        
        this.modified = false;
        this.updateTotals();
    }

    async savePiece() {
        if (!this.validatePiece()) return;
        
        try {
            // Préparer les données
            const pieceData = {
                journal_pk: this.currentJournal,
                date: this.elements.pieceDate.value,
                piece: this.elements.pieceNumber.value,
                reference: this.elements.pieceRef.value,
                lignes: this.getGridData()
            };
            
            // Sauvegarder
            const result = await this.api.savePiece(pieceData);
            
            if (result.success) {
                this.showSuccess('Pièce sauvegardée avec succès');
                this.modified = false;
                this.newPiece(); // Préparer une nouvelle pièce
            } else {
                this.showError(result.error || 'Erreur lors de la sauvegarde');
            }
            
        } catch (error) {
            this.showError('Erreur lors de la sauvegarde : ' + error.message);
        }
    }

    getGridData() {
        const lines = [];
        const rows = document.querySelectorAll('#sageGrid tbody tr');
        
        rows.forEach(row => {
            const line = {
                jour: row.querySelector('[data-column="jour"]')?.value,
                compte: row.querySelector('[data-column="compte"]')?.value,
                tiers: row.querySelector('[data-column="tiers"]')?.value,
                libelle: row.querySelector('[data-column="libelle"]')?.value,
                echeance: row.querySelector('[data-column="echeance"]')?.value,
                debit: this.parseAmount(row.querySelector('[data-column="debit"]')?.value),
                credit: this.parseAmount(row.querySelector('[data-column="credit"]')?.value)
            };
            
            // Ne pas inclure les lignes vides
            if (line.compte || line.debit || line.credit) {
                lines.push(line);
            }
        });
        
        return lines;
    }

    validatePiece() {
        // Vérifier les champs obligatoires
        if (!this.elements.pieceDate.value) {
            this.showError('La date est obligatoire');
            return false;
        }
        
        if (!this.elements.pieceNumber.value) {
            this.showError('Le numéro de pièce est obligatoire');
            return false;
        }
        
        // Vérifier l'équilibre
        const { totalDebit, totalCredit } = this.calculateTotals();
        if (Math.abs(totalDebit - totalCredit) > 0.01) {
            this.showError('La pièce n\'est pas équilibrée');
            return false;
        }
        
        return true;
    }

    clearGrid() {
        const tbody = this.gridElement.querySelector('tbody');
        tbody.innerHTML = '';
        this.addNewLine(); // Ajouter une ligne vide
    }

    getPieceData() {
        return {
            journal_pk: this.journalId,
            numero: document.getElementById('pieceNumber').value,
            date: document.getElementById('pieceDate').value,
            reference: document.getElementById('pieceRef').value,
            lines: this.getGridLines()
        };
    }

    getGridLines() {
        const lines = [];
        const rows = this.gridElement.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const line = {
                compte: row.querySelector('[data-column="compte"]')?.value,
                libelle: row.querySelector('[data-column="libelle"]')?.value,
                debit: this.parseAmount(row.querySelector('[data-column="debit"]')?.value),
                credit: this.parseAmount(row.querySelector('[data-column="credit"]')?.value),
                echeance: row.querySelector('[data-column="echeance"]')?.value,
                tiers: row.querySelector('[data-column="tiers"]')?.value
            };
            
            // Ne pas inclure les lignes vides
            if (line.compte || line.debit > 0 || line.credit > 0) {
                lines.push(line);
            }
        });
        
        return lines;
    }

    addNewLine() {
        const tbody = this.gridElement.querySelector('tbody');
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td><input type="text" class="account account-search" data-column="compte" tabindex="1"></td>
            <td><input type="text" class="label" data-column="libelle" tabindex="2"></td>
            <td><input type="text" class="debit" data-column="debit" value="0,00" tabindex="3"></td>
            <td><input type="text" class="credit" data-column="credit" value="0,00" tabindex="4"></td>
            <td><input type="date" class="due-date" data-column="echeance" tabindex="5"></td>
            <td><input type="text" class="tiers tiers-search" data-column="tiers" tabindex="6"></td>
        `;
        
        tbody.appendChild(tr);
        return tr;
    }

    parseAmount(value) {
        if (!value) return 0;
        return parseFloat(value.replace(/\s/g, '').replace(',', '.')) || 0;
    }

    formatAmount(value) {
        return value.toLocaleString('fr-FR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    initializeGrid() {
        this.clearGrid();
        
        // Suggérer un nouveau numéro de pièce
        this.api.getSuggestedPieceNumber()
            .then(response => {
                if (response.success) {
                    document.getElementById('pieceNumber').value = response.numero;
                }
            });
        
        // Initialiser la date
        document.getElementById('pieceDate').value = new Date().toISOString().split('T')[0];
        
        // Vider la référence
        document.getElementById('pieceRef').value = '';
        
        this.modified = false;
    }

    markAsModified() {
        this.modified = true;
        document.getElementById('statusMessage').textContent = 'Modifié';
    }
}