// NOTE: For NAMC to ICD
// when the return button is clicked it returns the current value in the search box to the backend.
function returnJson() {
	const icdValue = document.getElementById("icdCode").value;
	const namcValue = document.getElementById("search-input").value;
	console.log(namcValue);
	console.log(icdValue);

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
const resultInput = document.getElementById('result-input');
const resultDiv = document.getElementById('result');

let isSuggestionSelected = false; // Track if a suggestion was selected
let isResultSelected = false; // Track if a suggestion was selected


//NOTE: Checks if any change is made to the NAMC Code search box
let debounceTimeout;

searchInput.addEventListener('input', () => {
	const query = searchInput.value.trim();
	isSuggestionSelected = false;
	submitButton.disabled = true;

	if (query.length === 0) {
		suggestionsContainer.style.display = 'none';
		return;
	}

	// Clear previous timeout
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

		terms = selectedTerm.split(",");
		term = terms[1];
		term = term.split(":")[1].trim();

		ECT.Handler.search("1", term);
		console.log(terms[1])


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
			const response = await fetch(url);
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
function returnJsonn() {
	const icdValue2 = document.getElementById("icdCode2").value;
	const namcValue2 = document.getElementById("search-input2").value;

	const payload2 = { icd: icdValue2, namc: namcValue2 };

	fetch("/api/returnJson", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
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
		const response = await fetch(url);
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


