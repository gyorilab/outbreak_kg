// Function to set up autocomplete for a field
const setupAutocomplete = (fieldId, endpoint) => {
  const inputField = document.getElementById(fieldId);
  const dataList = document.getElementById(`${fieldId}_options`);

  // Listen for input events on the field
  inputField.addEventListener('input', async () => {
    const query = inputField.value.trim();

    // Only make a request if the input has some text
    if (query.length > 0) {
      try {
        const response = await fetch(`/autocomplete/${endpoint}?prefix=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Could not fetch autocomplete suggestions');

        const suggestions = await response.json(); // Expecting the server to return a JSON array

        // Clear the current options in the datalist
        dataList.innerHTML = '';

        // Populate the datalist with new options
        suggestions.forEach(suggestion => {
          // Check if the suggestion is an array of length 4
          let matchText = "";
          let gndName = "";
          let curie = "";
          let description = "";
          if (Array.isArray(suggestion) && suggestion.length === 4) {
            [matchText, gndName, curie, description] = suggestion;
            if (gndName) {
              gndName = ` (${gndName})`;
            }
          } else if (typeof suggestion === 'string') {
            curie = suggestion;
            matchText = suggestion;
          }
          const option = document.createElement('option');
          option.value = curie;
          // Todo: Add a description to the option or scrap description altogether?
          option.textContent = `${matchText}${gndName}`;
          dataList.appendChild(option);
        });
      } catch (error) {
        console.error('Error fetching autocomplete suggestions:', error);
      }
    }
  });
};