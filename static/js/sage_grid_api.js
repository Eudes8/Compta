/**
 * Sage Grid API - JavaScript module for interacting with the Sage Grid backend
 */
class SageGridAPI {
    constructor(config) {
        this.baseUrl = config.baseUrl || '';
        this.csrfToken = config.csrfToken || '';
        this.dossierId = config.dossierId;
        this.journalId = config.journalId;
        this.annee = config.annee;
        this.mois = config.mois;
    }

    /**
     * Save a grid entry to the server
     * @param {Object} headerData - Header data for the accounting entry
     * @param {Array} gridData - Grid data for the accounting entry lines
     * @returns {Promise} - Promise with the server response
     */
    saveEntry(headerData, gridData) {
        const url = `${this.baseUrl}/api/dossier/${this.dossierId}/journal/${this.journalId}/${this.annee}/${this.mois}/save-entry/`;
        
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
            },
            body: JSON.stringify({
                header: headerData,
                grid: gridData
            })
        }).then(response => response.json());
    }

    /**
     * Search for accounts matching a query
     * @param {string} query - Search query
     * @returns {Promise} - Promise with the search results
     */
    searchAccounts(query) {
        const url = `${this.baseUrl}/api/dossier/${this.dossierId}/search-accounts/?q=${encodeURIComponent(query)}`;
        
        return fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        }).then(response => response.json());
    }

    /**
     * Search for tiers (customers/vendors) matching a query
     * @param {string} query - Search query
     * @returns {Promise} - Promise with the search results
     */
    searchTiers(query) {
        const url = `${this.baseUrl}/api/dossier/${this.dossierId}/search-tiers/?q=${encodeURIComponent(query)}`;
        
        return fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        }).then(response => response.json());
    }

    /**
     * Get data for an existing accounting entry
     * @param {number} pieceId - ID of the accounting entry
     * @returns {Promise} - Promise with the entry data
     */
    getPieceData(pieceId) {
        const url = `${this.baseUrl}/api/piece/${pieceId}/data/`;
        
        return fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        }).then(response => response.json());
    }

    /**
     * Get journal type and information
     * @param {number} journalId - Journal ID
     * @returns {Promise} - Promise with journal info
     */
    getJournalInfo(journalId) {
        const url = `${this.baseUrl}/api/journal/${journalId}/info/`;
        return fetch(url).then(response => response.json());
    }

    /**
     * Search for business partners (tiers)
     * @param {string} query - Search query
     * @param {string} journalType - Type of journal (AC, VE, etc.)
     * @returns {Promise} - Promise with search results
     */
    searchTiers(query, journalType) {
        const url = `${this.baseUrl}/api/dossier/${this.dossierId}/tiers-lookup/?` + 
                   `query=${encodeURIComponent(query)}&journal_type=${encodeURIComponent(journalType)}`;
        
        return fetch(url).then(response => response.json());
    }

    /**
     * Save a complete accounting document
     * @param {Object} pieceData - Complete accounting document data
     * @returns {Promise} - Promise with save result
     */
    savePiece(pieceData) {
        const url = `${this.baseUrl}/api/piece/save/`;
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(pieceData)
        }).then(response => response.json());
    }

    /**
     * Get data for an adjacent piece (previous or next)
     * @param {string} currentPiece - Current piece number
     * @param {string} direction - 'prev' or 'next'
     * @returns {Promise} - Promise with adjacent piece data
     */
    getAdjacentPiece(currentPiece, direction) {
        const url = `${this.baseUrl}/api/dossier/${this.dossierId}/journal/${this.journalId}/piece/${currentPiece}/${direction}/`;
        return fetch(url).then(response => response.json());
    }

    /**
     * Delete an accounting piece
     * @param {string} pieceNumber - Piece number to delete
     * @returns {Promise} - Promise with delete result
     */
    deletePiece(pieceNumber) {
        const url = `${this.baseUrl}/api/piece/${pieceNumber}/delete/`;
        return fetch(url, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': this.csrfToken
            }
        }).then(response => response.json());
    }

    /**
     * Search for pieces based on criteria
     * @param {Object} criteria - Search criteria
     * @returns {Promise} - Promise with search results
     */
    searchPieces(criteria) {
        const params = new URLSearchParams();
        Object.entries(criteria).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });

        const url = `${this.baseUrl}/api/dossier/${this.dossierId}/journal/${this.journalId}/search-pieces/?${params}`;
        return fetch(url).then(response => response.json());
    }

    /**
     * Get suggested piece number for new piece
     * @returns {Promise} - Promise with suggested number
     */
    getSuggestedPieceNumber() {
        const url = `${this.baseUrl}/api/dossier/${this.dossierId}/journal/${this.journalId}/suggest-piece-number/`;
        return fetch(url).then(response => response.json());
    }

    /**
     * Validate piece data before saving
     * @param {Object} pieceData - Piece data to validate
     * @returns {Promise} - Promise with validation result
     */
    validatePieceData(pieceData) {
        const url = `${this.baseUrl}/api/piece/validate/`;
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(pieceData)
        }).then(response => response.json());
    }
}

/**
 * Initialize the Sage Grid API with configuration from the page
 */
function initSageGridAPI() {
    // Get configuration from data attributes on the grid container
    const gridContainer = document.querySelector('.sage-window');
    
    if (!gridContainer) {
        console.error('Sage grid container not found');
        return null;
    }
    
    // Extract configuration from data attributes
    const config = {
        baseUrl: '',  // Base URL is the current domain
        csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        dossierId: gridContainer.dataset.dossierId,
        journalId: gridContainer.dataset.journalId,
        annee: gridContainer.dataset.annee,
        mois: gridContainer.dataset.mois
    };
    
    // Ensure all required parameters are present
    if (!config.csrfToken || !config.dossierId || !config.journalId || !config.annee || !config.mois) {
        console.error('Missing required configuration for SageGridAPI', config);
        return null;
    }
    
    return new SageGridAPI(config);
}

// Export the API for use in other modules
if (typeof module !== 'undefined') {
    module.exports = { SageGridAPI, initSageGridAPI };
}