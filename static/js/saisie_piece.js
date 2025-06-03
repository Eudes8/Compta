/**
 * Gestionnaire de saisie des écritures comptables
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des totaux
    updateTotals();

    // Ajouter les écouteurs d'événements pour la mise à jour des totaux
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('debit-input') || e.target.classList.contains('credit-input')) {
            const row = e.target.closest('.ligne-ecriture');
            const debitInput = row.querySelector('.debit-input');
            const creditInput = row.querySelector('.credit-input');
            
            // Si on saisit un débit, on vide le crédit et vice versa
            if (e.target.classList.contains('debit-input') && e.target.value) {
                creditInput.value = '';
            } else if (e.target.classList.contains('credit-input') && e.target.value) {
                debitInput.value = '';
            }
            
            updateTotals();
        }
    });

    // Navigation avec Tab
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            const row = e.target.closest('.ligne-ecriture');
            const isLastInput = e.target.classList.contains('tiers-input');
            const isLastRow = row === document.querySelector('.ligne-ecriture:last-child');
            
            if (isLastInput && isLastRow && !e.shiftKey) {
                e.preventDefault();
                ajouterNouvelleLigne();
            }
        }
    });

    // Boutons de la barre d'outils
    document.getElementById('btnNouveau').addEventListener('click', function() {
        if (confirm('Voulez-vous créer une nouvelle pièce ? Les modifications non sauvegardées seront perdues.')) {
            reinitialiserSaisie();
        }
    });

    document.getElementById('btnSupprimer').addEventListener('click', function() {
        const ligneActive = document.querySelector('.ligne-ecriture:focus-within');
        if (ligneActive) {
            ligneActive.remove();
            updateTotals();
        }
    });

    document.getElementById('btnEnregistrer').addEventListener('click', sauvegarderPiece);
});

// Fonctions utilitaires
function updateTotals() {
    let totalDebit = 0;
    let totalCredit = 0;
    
    // Récupérer toutes les lignes d'écriture
    document.querySelectorAll('.ligne-ecriture').forEach(ligne => {
        const debit = parseFloat(ligne.querySelector('.debit-input').value) || 0;
        const credit = parseFloat(ligne.querySelector('.credit-input').value) || 0;
        totalDebit += debit;
        totalCredit += credit;
    });

    // Mettre à jour les totaux
    document.getElementById('totalDebit').textContent = totalDebit.toFixed(2);
    document.getElementById('totalCredit').textContent = totalCredit.toFixed(2);
    
    // Calculer et afficher le solde
    const solde = totalDebit - totalCredit;
    const balanceElement = document.getElementById('balance');
    balanceElement.textContent = Math.abs(solde).toFixed(2);
    
    // Mise à jour visuelle du solde
    const balanceRow = balanceElement.closest('.sage-i7-balance');
    balanceRow.classList.remove('balanced', 'unbalanced');
    balanceRow.classList.add(solde === 0 ? 'balanced' : 'unbalanced');
}

function ajouterNouvelleLigne() {
    const tbody = document.querySelector('.sage-i7-grid tbody');
    const lastRow = tbody.lastElementChild;
    const newIndex = parseInt(lastRow.dataset.index) + 1;
    
    const newRow = document.createElement('tr');
    newRow.className = 'ligne-ecriture';
    newRow.dataset.index = newIndex;
    
    newRow.innerHTML = `
        <td>
            <input type="text" name="lignes-${newIndex}-compte" 
                   class="form-control form-control-sm compte-input" 
                   placeholder="Compte..." 
                   autocomplete="off"
                   data-lookup="true">
        </td>
        <td>
            <input type="text" name="lignes-${newIndex}-libelle" 
                   class="form-control form-control-sm"
                   placeholder="Libellé...">
        </td>
        <td>
            <input type="number" name="lignes-${newIndex}-debit" 
                   class="form-control form-control-sm montant-input debit-input"
                   step="0.01" min="0">
        </td>
        <td>
            <input type="number" name="lignes-${newIndex}-credit"
                   class="form-control form-control-sm montant-input credit-input"
                   step="0.01" min="0">
        </td>
        <td>
            <input type="date" name="lignes-${newIndex}-echeance"
                   class="form-control form-control-sm">
        </td>
        <td>
            <input type="text" name="lignes-${newIndex}-tiers"
                   class="form-control form-control-sm tiers-input"
                   placeholder="Tiers..."
                   data-lookup="true">
        </td>
        <td class="text-center">
            <button type="button" class="btn btn-sm btn-danger" onclick="supprimerLigne(this)">
                <i class="fas fa-times"></i>
            </button>
        </td>
    `;
    
    tbody.appendChild(newRow);
    newRow.querySelector('.compte-input').focus();
}

function supprimerLigne(btn) {
    const tbody = btn.closest('tbody');
    if (tbody.children.length > 1) {
        btn.closest('tr').remove();
        updateTotals();
    } else {
        // Ne pas supprimer la dernière ligne, juste la vider
        const inputs = btn.closest('tr').querySelectorAll('input');
        inputs.forEach(input => input.value = '');
        updateTotals();
    }
}

function reinitialiserSaisie() {
    // Vider les en-têtes
    document.getElementById('pieceNumber').value = '';
    document.getElementById('pieceDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('pieceRef').value = '';
    
    // Supprimer toutes les lignes sauf une
    const tbody = document.querySelector('.sage-i7-grid tbody');
    tbody.innerHTML = '';
    ajouterNouvelleLigne();
    
    updateTotals();
}

async function sauvegarderPiece() {
    // Vérifier l'équilibre
    const totalDebit = parseFloat(document.getElementById('totalDebit').textContent);
    const totalCredit = parseFloat(document.getElementById('totalCredit').textContent);
    
    if (Math.abs(totalDebit - totalCredit) > 0.01) {
        alert("La pièce n'est pas équilibrée. Impossible de sauvegarder.");
        return;
    }
    
    // Vérifier qu'il y a au moins une ligne valide
    const lignes = document.querySelectorAll('.ligne-ecriture');
    let hasValidLine = false;
    
    lignes.forEach(ligne => {
        const compte = ligne.querySelector('.compte-input').value;
        const debit = parseFloat(ligne.querySelector('.debit-input').value) || 0;
        const credit = parseFloat(ligne.querySelector('.credit-input').value) || 0;
        
        if (compte && (debit > 0 || credit > 0)) {
            hasValidLine = true;
        }
    });
    
    if (!hasValidLine) {
        alert("Veuillez saisir au moins une ligne avec un compte et un montant.");
        return;
    }
    
    // Si tout est valide, soumettre le formulaire
    document.querySelector('form').submit();
}
