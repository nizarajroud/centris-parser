fetch("https://passerelle.centris.ca/redirect.aspx?NoMLS=23215645&Lang=F&source=centris.ca")
  .then(response => console.log("Final URL:", response.url));
