function handleValueChange(selectElement,name) {
    var value = selectElement.value;
    var currentLocation = window.location.href;

    if (currentLocation.includes('&' + name + '=' + value)) {
        var regex = new RegExp('&' + name + '=' + value, 'g');
        window.location.href = currentLocation.replace(regex, '');
    } else {
        window.location.href = currentLocation + '&' + name + '=' + value;
    }
}
