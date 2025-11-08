// NOTE: For NAMC to ICD
// when the return button is clicked it returns the current value in the search box to the backend.

function returnJson() {
	const icdValue = document.getElementById("icdCode").value;
	const namcValue = document.getElementById("search-input").value;

	const payload = { icd: icdValue, namc: namcValue };

	fetch("/api/returnJson", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload)
	}).catch(error => console.error("Error:", error));
}

// script.js
const searchInput = document.getElementById('search-input');
const suggestionsContainer = document.getElementById('suggestions');
const submitButton = document.getElementById('submit-button');
const icdCodeInput = document.getElementById('icdCode'); 

let isSuggestionSelected = false; 
let isResultSelected = false; 

let debounceTimeout;

//NOTE: Checks if any change is made to the NAMC Code search box
searchInput.addEventListener('input', async () => {
	const query = searchInput.value.trim();
	isSuggestionSelected = false; 
	submitButton.disabled = true; 

	if (query.length === 0) {
		suggestionsContainer.style.display = 'none';
		return;
	}

	clearTimeout(debounceTimeout);

	// Set new debounce
	debounceTimeout = setTimeout(async () => {
		try {
			const url = "/api/suggestions?q=" + encodeURIComponent(query);
			const response = await fetch(url);
			if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);

			const suggestions = await response.json();
			console.log('Suggestions:', suggestions); // Debug

			suggestionsContainer.innerHTML = '';

			if (suggestions.length > 0) {
				suggestions.forEach(item => {
					const div = document.createElement('div');
					div.className = 'suggestion-item';
					div.textContent = item; // item is [code, display, definition]
					div.addEventListener('click', () => {
						searchInput.value = item; // Store the full string
						suggestionsContainer.style.display = 'none';
						isSuggestionSelected = true;
						submitButton.disabled = false;
					});
					suggestionsContainer.appendChild(div);
				});
				suggestionsContainer.style.display = 'block';
			} else {
				suggestionsContainer.style.display = 'none';
			}
		} catch (error) {
			console.error('Error fetching suggestions:', error);
			suggestionsContainer.style.display = 'none';
		}
	}, 800);
});




// =================================================================
// (NAMC-to-ICD) Convert Button Logic
// =================================================================
submitButton.addEventListener('click', async () => {
	if (!isSuggestionSelected) {
		alert('Please select a suggestion from the list.');
		return;
	}

    // Capture the full selected term, which should be in the format: "CODE, DISPLAY, DEFINITION"
	const fullSelectedTerm = searchInput.value.trim();
    // Attempt to extract the NAMC code from the selected term for the main form
    const searchNamcCode = fullSelectedTerm.split(',')[0].trim(); 

	if (!fullSelectedTerm) {
		alert('No term selected.');
		return;
	}

	try {
		// Set loading state
		icdCodeInput.value = "Searching (ConceptMap & Flexisearch)...";
        suggestionsContainer.innerHTML = '';
        suggestionsContainer.style.display = 'none';

		// 1. Call our new smart /api/submit endpoint
		const response = await fetch("/api/submit", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ term: fullSelectedTerm })
		});

		if (!response.ok) {
			throw new Error(`Server error: ${response.status}`);
		}

		// Get the new response object
		const responseData = await response.json(); 
		const source = responseData.source; // "map", "flexi", or "none"
		const data = responseData.data;     // [[code, title], ...]

        // NEW: Display results in the main form's preview section
        const mainFormPreview = document.getElementById('preview');
        if (mainFormPreview) {
            mainFormPreview.hidden = false;
            mainFormPreview.textContent = `Source: ${source} | Matches: ${data.length}\n` + JSON.stringify(data, null, 2);
        }

		// 2. Check the response
		if (source === "map" || source === "flexi") {
			// SUCCESS: We found matches!
            icdCodeInput.value = "Found " + data.length + " matches. Select one below.";
            
            // 3. Display the results with the correct style
            let cssClass = (source === "map") ? "suggestion-item-map" : "suggestion-item-flexi";
            
            // Add header for Flexisearch
            if (source === "flexi") {
                const header = document.createElement('div');
                header.className = 'suggestions-header';
                header.textContent = 'Flexisearch';
                suggestionsContainer.appendChild(header);
            }

			data.forEach(item => { // item is [code, title]
                const code = item[0];
                const title = item[1];
				const div = document.createElement('div');
				div.className = cssClass; // Apply the correct class
				div.textContent = `${code}, ${title}`;
				div.addEventListener('click', () => {
                    // When clicked, populate the ICD box in the drawer
					icdCodeInput.value = `${code}, ${title}`;
					suggestionsContainer.style.display = 'none';
                    
                    // NEW: Push ICD code to the main form's ICD field
                    const mainIcdInput = document.getElementById('icd');
                    if (mainIcdInput) {
                        mainIcdInput.value = code;
                    }

                    // NEW: Push NAMC code to the main form's NAMC field
                    const mainNamcInput = document.getElementById('namc');
                    if (mainNamcInput) {
                        mainNamcInput.value = searchNamcCode;
                    }
                    
                    // Update combined display in main form
                    if (typeof updateCombined === 'function') updateCombined(); 
				});
				suggestionsContainer.appendChild(div);
			});
			suggestionsContainer.style.display = 'block'; // Show the list
		
		} else {
			// FAILURE: Server's smart search found nothing (source === "none")
			icdCodeInput.value = "No ConceptMap or Flexisearch matches found. Opening manual search...";
            
            // 4. Fallback to the WHO embedded tool as a last resort
			const terms = fullSelectedTerm.split(","); 
			const englishTerm = terms[1].split(": ")[1] || terms[1]; 
			
			ECT.Handler.search("1", englishTerm); 
		}

	} catch (error) {
		console.error('Error submitting term:', error);
		icdCodeInput.value = `Error: ${error.message}`;
        
        // NEW: Display error in the main form's preview section
        const mainFormPreview = document.getElementById('preview');
        if (mainFormPreview) {
            mainFormPreview.hidden = false;
            mainFormPreview.textContent = `ERROR during NAMC->ICD conversion: ${error.message}`;
        }
	}
});
// =================================================================
// END: (NAMC-to-ICD)
// =================================================================


// NOTE: This is for the WHO ECT

const mySettings = {
	apiServerUrl: "https://id.who.int",
	apiSecured: true,
	popupMode: false, // This makes the tool embed in the page
	searchByCodeOrURI: true,
	flexisearchAvailable: true
};


const myCallbacks = {

	getNewTokenFunction: async () => {
		const url = "/api/newToken";
		try {
			const response = await fetch(url);
			const result = await response.json();
			return result.token;
		} catch (e) {
			console.log("Error during the request", e);
			return null;
		}
	},

    // *** UPDATED THIS FUNCTION ***
	selectedEntityFunction: (selectedEntity, ctwObject) => {
		
        // This handles the fallback search for the TOP converter
		if (selectedEntity.iNo == 1) {
			ECT.Handler.clear("1");
			document.getElementById('icdCode').value = `${selectedEntity.code} , ${selectedEntity.title}`;
            
            // NEW: Push ICD code to the main form's ICD field
            const mainIcdInput = document.getElementById('icd');
            if (mainIcdInput) {
                mainIcdInput.value = selectedEntity.code;
            }
            
            // Also push the NAMC code used for the search to the main form's NAMC field
            // The NAMC code is expected to be in searchInput.value
            const fullSelectedTerm = searchInput.value.trim();
            const searchNamcCode = fullSelectedTerm.split(',')[0].trim(); 
            const mainNamcInput = document.getElementById('namc');
            if (mainNamcInput) {
                mainNamcInput.value = searchNamcCode;
            }

            if (typeof updateCombined === 'function') updateCombined(); 

            // NEW: Display selection in the main form's preview section
            const mainFormPreview = document.getElementById('preview');
            if (mainFormPreview) {
                mainFormPreview.hidden = false;
                mainFormPreview.textContent = `ICD Selection (iNo 1): ${selectedEntity.code}, ${selectedEntity.title}`;
            }
		}
        // This handles the primary search for the BOTTOM converter
        else {
			ECT.Handler.clear("2");
			document.getElementById('icdCode2').value = `${selectedEntity.code} , ${selectedEntity.title}`;
			submitButton2.disabled = false; // Enable convert button
            
            // NEW: Display selection in the main form's preview section
            const mainFormPreview = document.getElementById('preview');
            if (mainFormPreview) {
                mainFormPreview.hidden = false;
                mainFormPreview.textContent = `ICD Search Term (iNo 2): ${selectedEntity.code}, ${selectedEntity.title}`;
            }
        }
	}
};


ECT.Handler.configure(mySettings, myCallbacks);


// =================================================================
// START: (ICD-to-NAMC) LOGIC
// =================================================================

// NOTE: For ICD to NAMC
// (This function is just for logging, not essential for the button)
function returnJson() {
	const icdValue2 = document.getElementById("icdCode2").value;
	const namcValue2 = document.getElementById("search-input2").value;

	const payload2 = { icd: icdValue2, namc: namcValue2 };

	fetch("/api/returnJson", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload2)
	}).catch(error => console.error("Error:", error));
}

// Get the elements for the second converter
const searchInput2 = document.getElementById('icdCode2');
const suggestionsContainer2 = document.getElementById('suggestions2');
const submitButton2 = document.getElementById('submit-button2');
const resultInput2 = document.getElementById('search-input2');


//NOTE: Checks if any change is made to the ICD-11 Code search box
// This listener enables the button *after* you select a WHO term
searchInput2.addEventListener('input', async () => {
	submitButton2.disabled = searchInput2.value.trim().length === 0;
});


//NOTE: Handle (ICD-to-NAMC) submit button click
submitButton2.addEventListener('click', async () => {
	const fullSelectedTerm = searchInput2.value.trim(); // e.g., "MA00, Fever of unknown origin"
    // Attempt to extract the ICD code from the selected term for the main form
    const searchIcdCode = fullSelectedTerm.split(',')[0].trim();
    
	if (!fullSelectedTerm) {
		return;
	}

    // Set loading state
    resultInput2.value = "Searching (Map & Fuzzy)...";
    suggestionsContainer2.innerHTML = '';
    suggestionsContainer2.style.display = 'none';

	try {
		const url = "/api/ICDtoNAMC?q=" + encodeURIComponent(fullSelectedTerm)
		const response = await fetch(url);
		if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);

		const suggestions = await response.json(); // List of map or fuzzy results
		
        // NEW: Display results in the main form's preview section
        const mainFormPreview = document.getElementById('preview');
        if (mainFormPreview) {
            mainFormPreview.hidden = false;
            mainFormPreview.textContent = `ICD->NAMC Results (${suggestions.length} matches):\n` + JSON.stringify(suggestions, null, 2);
        }

		if (suggestions.length > 0) {
            
            resultInput2.value = "Found " + suggestions.length + " matches. Select below.";

            // Check the score of the first result to see what kind of results they are
            // Map results have score 101, fuzzy results have score < 100
            let isMapResult = suggestions[0].score > 100;
            let cssClass = isMapResult ? 'suggestion-item-map' : 'suggestion-item-fuzzy';
            
            if (!isMapResult) {
                const header = document.createElement('div');
                header.className = 'suggestions-header';
                header.textContent = 'Fuzzy Matches';
                suggestionsContainer2.appendChild(header);
            }

			suggestions.forEach(item => {
				const div2 = document.createElement('div');
				div2.className = cssClass; // Apply map or fuzzy class
				div2.textContent = `${item.code}, ${item.term} (Score: ${item.score.toFixed(0)})`; 
				div2.addEventListener('click', () => {
					resultInput2.value = `${item.code}, ${item.term}`;
					suggestionsContainer2.style.display = 'none';
                    
                    // NEW: Push NAMC code to the main form's NAMC field
                    const mainNamcInput = document.getElementById('namc');
                    if (mainNamcInput) {
                        mainNamcInput.value = item.code;
                    }

                    // NEW: Push ICD code to the main form's ICD field
                    const mainIcdInput = document.getElementById('icd');
                    if (mainIcdInput) {
                        mainIcdInput.value = searchIcdCode;
                    }
                    
                    // Update combined display in main form
                    if (typeof updateCombined === 'function') updateCombined(); 
				});
				suggestionsContainer2.appendChild(div2);
			});
			suggestionsContainer2.style.display = 'block';
		} else {
			// No matches found in the map OR fuzzy search
			resultInput2.value = 'No Map or Fuzzy matches found.';
			suggestionsContainer2.style.display = 'none';
		}

	} catch (error) {
		console.error('Error submitting term:', error);
        resultInput2.value = "Error during search.";

        // NEW: Display error in the main form's preview section
        const mainFormPreview = document.getElementById('preview');
        if (mainFormPreview) {
            mainFormPreview.hidden = false;
            mainFormPreview.textContent = `ERROR during ICD->NAMC conversion: ${error.message}`;
        }
	}
});
// =================================================================
// END: (ICD-to-NAMC) LOGIC
// =================================================================



// ====================================================================
// START: NLP CLINICAL NOTES SEARCH LOGIC
// ====================================================================
const nlpSearchButton = document.getElementById('nlp-search-button');
const nlpSearchInput = document.getElementById('nlp-search-input');
const nlpResultsArea = document.getElementById('nlp-results-area');
const nlpSpinner = document.getElementById('nlp-search-spinner');

if (nlpSearchButton) {
	nlpSearchButton.addEventListener('click', handleNLPSearch);
}

// Allow pressing Ctrl+Enter or Cmd+Enter to trigger the search
if (nlpSearchInput) {
	nlpSearchInput.addEventListener('keydown', (event) => {
		if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			event.preventDefault(); // Prevent new line in textarea
			handleNLPSearch();
		}
	});
}

async function handleNLPSearch() {
	const query = nlpSearchInput.value.trim();
	if (!query) {
		alert('Please enter a clinical description to search.');
		return;
	}

	// Show a loading state
	nlpSpinner.classList.remove('d-none');
	nlpSearchButton.disabled = true;
	nlpResultsArea.innerHTML = ''; // Clear previous results

	try {
		const response = await fetch('/api/nlp_search', {
			method: 'POST',
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ query: query }),
		});

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
		}

		const results = await response.json();
        
        // NEW: Display results in the main form's preview section
        const mainFormPreview = document.getElementById('preview');
        if (mainFormPreview) {
            mainFormPreview.hidden = false;
            mainFormPreview.textContent = `NLP Search Results (${results.length} matches):\n` + JSON.stringify(results, null, 2);
        }

		displayNLPResults(results);

	} catch (error) {
		console.error('NLP Search Error:', error);
		nlpResultsArea.innerHTML = `<div class="alert alert-danger">An error occurred: ${error.message}</div>`;
	} finally {
		// Restore button to normal state
		nlpSpinner.classList.add('d-none');
		nlpSearchButton.disabled = false;
	}
}

function displayNLPResults(results) {
	if (!results || results.length === 0) {
		nlpResultsArea.innerHTML = '<div class="alert alert-warning text-center">No relevant terms found for the given description.</div>';
		return;
	}

	// Map system names to Bootstrap badge colors for clear visual distinction
	const systemColors = {
		"Siddha": "bg-primary",
		"Ayurveda": "bg-success",
		"Unani": "bg-info"
	};

	const resultsHtml = results.map(item => {
		const badgeColor = systemColors[item.system] || 'bg-secondary';
		// Remove the redundant term from the definition for cleaner display
		const cleanDefinition = item.full_definition.replace(item.display + ': ', '');

		return `
						<div class="card shadow-sm mb-3" onclick="handleNLPCardClick('${item.code}', '${item.display}', '${item.system}')">
							<div class="card-body">
								<div class="d-flex justify-content-between align-items-start">
									<h5 class="card-title mb-1">${item.display}</h5>
									<span class="badge ${badgeColor} fs-6">${item.system}</span>
								</div>
								<h6 class="card-subtitle mb-2 text-muted">Code: ${item.code}</h6>
								<p class="card-text small mt-2">${cleanDefinition}</p>
							</div>
						</div>
					`;
	}).join('');

	window.handleNLPCardClick = function(code, display, system) {
		// This function is now globally available
		console.log("NLP Card clicked:", code, display, system);
		
		// Find the original full item from the suggestions to populate the input
		const fullDisplay = `${system}: ${display}`;
		
		// We need to find the vernacular term to match the autocomplete format
		// This is a bit of a hack, we'll just leave it empty
		const fullTermString = `${code},${fullDisplay},`; 

		searchInput.value = fullTermString;
		
		// Scroll to the top to see the converter
		window.scrollTo(0, 0);

		// Enable the convert button
        isSuggestionSelected = true; 
        submitButton.disabled = false;
        
        // NEW: Push the NAMC code to the main form's NAMC field
        const mainNamcInput = document.getElementById('namc');
        if (mainNamcInput) {
            mainNamcInput.value = code;
        }

        // NEW: Clear the ICD field as NLP only gives a NAMC term/code
        const mainIcdInput = document.getElementById('icd');
        if (mainIcdInput) {
            mainIcdInput.value = '';
        }

        if (typeof updateCombined === 'function') updateCombined(); 
	}

	nlpResultsArea.innerHTML = resultsHtml;
}
// =V==================================
// END: NLP CLINICAL NOTES SEARCH LOGIC
// ===================================