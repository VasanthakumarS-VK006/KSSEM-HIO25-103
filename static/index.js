// NOTE: For NAMC to ICD
// when the return button is clicked it returns the current value in the search box to the backend.

let token = null;

async function initializeToken() {
	token = await getToken();  // Waits and assigns token
	console.log("Token initialized:", token);
}

async function getToken() {
	const response = await fetch("/api/generate-token", {
		method: "POST",
		headers: { 'Authorization': `Bearer ${token}`, "Content-Type": "application/json" },
		body: JSON.stringify({ abha_number: "12345678901234", abha_address: "patient@sbx", name: "Test User" })
	});
	const data = await response.json();
	return data.token;
}

initializeToken();

console.log(token)

function returnJson() {
	const icdValue = document.getElementById("icdCode").value;
	const namcValue = document.getElementById("search-input").value;

	const payload = { icd: icdValue, namc: namcValue };

	fetch("/api/returnJson", {
		method: "POST",
		headers: { 'Authorization': `Bearer ${token}`, "Content-Type": "application/json" },
		body: JSON.stringify(payload)
	}).catch(error => console.error("Error:", error));
}

// script.js
const searchInput = document.getElementById('search-input');
const suggestionsContainer = document.getElementById('suggestions');
const submitButton = document.getElementById('submit-button');
const resultInput = document.getElementById('result-input');
const resultDiv = document.getElementById('result');

let isSuggestionSelected = false; // Track if a suggestion was selected
let isResultSelected = false; // Track if a suggestion was selected

let debounceTimeout;

//NOTE: Checks if any change is made to the NAMC Code search box
searchInput.addEventListener('input', async () => {
	const query = searchInput.value.trim();
	isSuggestionSelected = false; // Reset on new input
	submitButton.disabled = true; // Disable button until suggestion is selected

	if (query.length === 0) {
		suggestionsContainer.style.display = 'none';
		return;
	}

	clearTimeout(debounceTimeout);

	// Set new debounce
	debounceTimeout = setTimeout(async () => {
		try {
			const url = "/api/suggestions?q=" + encodeURIComponent(query);
			const response = await fetch(url, { method: 'GET', headers: { 'Authorization': `Bearer ${token}` } });
			if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);

			const suggestions = await response.json();
			console.log('Suggestions:', suggestions); // Debug

			suggestionsContainer.innerHTML = '';

			if (suggestions.length > 0) {
				suggestions.forEach(item => {
					const div = document.createElement('div');
					div.className = 'suggestion-item';
					div.textContent = item;
					div.addEventListener('click', () => {
						searchInput.value = item;
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




//NOTE: Handle submit button click
submitButton.addEventListener('click', async () => {
	if (!isSuggestionSelected) {
		resultDiv.innerHTML = '<p>Please select a suggestion from the list.</p>';
		return;
	}

	const selectedTerm = searchInput.value.trim();
	if (!selectedTerm) {
		resultDiv.innerHTML = '<p>No term selected.</p>';
		return;
	}

	try {

		terms = selectedTerm.split(",")
		ECT.Handler.search("1", terms[1]);


	} catch (error) {
		console.error('Error submitting term:', error);
		resultDiv.innerHTML = `<p>Error: ${error.message}</p>`;
	}
});



// NOTE: This is for the WHO ECT

const mySettings = {
	apiServerUrl: "https://id.who.int",
	apiSecured: true,
	popupMode: true,
	searchByCodeOrURI: true,
	flexisearchAvailable: true
};


const myCallbacks = {

	getNewTokenFunction: async () => {
		const url = "/api/newToken";
		try {
			const response = await fetch(url, { method: 'GET', headers: { 'Authorization': `Bearer ${token}` } });
			const result = await response.json();
			return result.token;
		} catch (e) {
			console.log("Error during the request", e);
			return null;
		}
	},

	selectedEntityFunction: (selectedEntity, ctwObject) => {
		// document.getElementById('icdCode').value = `${selectedEntity.code} - ${selectedEntity.title}`;

		if (selectedEntity.iNo == 1) {
			ECT.Handler.clear("1");
			document.getElementById('icdCode').value = `${selectedEntity.code} , ${selectedEntity.title}`;
		}
		else {
			ECT.Handler.clear("2");
			document.getElementById('icdCode2').value = `${selectedEntity.code} , ${selectedEntity.title}`;
			submitButton2.disabled = false; // Enable submit button
		}
	}
};


ECT.Handler.configure(mySettings, myCallbacks);





// NOTE: For ICD to NAMC

function returnJson() {
	const icdValue2 = document.getElementById("icdCode2").value;
	const namcValue2 = document.getElementById("search-input2").value;

	const payload2 = { icd: icdValue2, namc: namcValue2 };

	fetch("/api/returnJson", {
		method: "POST",
		headers: { 'Authorization': `Bearer ${token}`, "Content-Type": "application/json" },
		body: JSON.stringify(payload2)
	}).catch(error => console.error("Error:", error));
}

// script.js
const searchInput2 = document.getElementById('icdCode2');
const suggestionsContainer2 = document.getElementById('suggestions2');
const submitButton2 = document.getElementById('submit-button2');
const resultInput2 = document.getElementById('search-input2');

let isSuggestionSelected2 = false; // Track if a suggestion was selected
let isResultSelected2 = false; // Track if a suggestion was selected


//NOTE: Checks if any change is made to the NAMC Code search box
searchInput2.addEventListener('input', async () => {
	const query2 = searchInput.value.trim();
	isSuggestionSelected2 = false; // Reset on new input
	submitButton2.disabled = true; // Disable button until suggestion is selected

	if (query2.length === 0) {
		suggestionsContainer2.style.display = 'none';
		return;
	}
});




//NOTE: Handle submit button click
submitButton2.addEventListener('click', async () => {
	console.log("Inside the submit's event listener")

	const selectedTerm = searchInput2.value.trim();
	console.log(selectedTerm)
	console.log("After displaying selectedTerm")
	if (!selectedTerm) {
		return;
	}

	try {

		console.log("Inside the submit's event listener")
		url = "/api/ICDtoNAMC?q=" + encodeURIComponent(selectedTerm)
		const response = await fetch(url, { method: 'GET', headers: { 'Authorization': `Bearer ${token}` } });
		if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);

		const suggestions = await response.json();
		console.log(suggestions)

		suggestionsContainer2.innerHTML = ''

		if (suggestions.length > 0) {
			suggestions.forEach(item => {
				const div2 = document.createElement('div');
				div2.className = 'suggestion-item';
				div2.textContent = `${item.code}, ${item.term}`; // English term
				div2.addEventListener('click', () => {
					resultInput2.value = `${item.code}, ${item.term}`;
					suggestionsContainer2.style.display = 'none';
				});
				suggestionsContainer2.appendChild(div2);
			});
			suggestionsContainer2.style.display = 'block';
		} else {
			suggestionsContainer2.style.display = 'none';
		}


	} catch (error) {
		console.error('Error submitting term:', error);
	}
});


// ====================================================================
// START: NLP CLINICAL NOTES SEARCH LOGIC (Works with the new main.py)
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
			headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
			body: JSON.stringify({ query: query }),
		});

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
		}

		const results = await response.json();
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
		console.log("Inside handleCardClickFunction");
		searchInput.value = `${code},${system}: ${display}`;
	}

	nlpResultsArea.innerHTML = resultsHtml;
}

// NOTE: This is for uploading csv into the backend

function uploadCSV() {
	var input = document.getElementById("csv-file-input");
	if (input.files.length == 0) {
		alert("Please pass a file into the box!!");
		return;
	}

	var data = new FormData();
	data.append("csv_file", input.files[0]);
	data.append("hfr_id",)

	fetch('/csvUpload', { 'Authorization': `Bearer ${token}`, method: "POST", body: data });

}



// ===================================
// END: NLP CLINICAL NOTES SEARCH LOGIC
// ===================================


