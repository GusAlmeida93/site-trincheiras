function handler(event) {
  var request = event.request;
  var host = request.headers.host ? request.headers.host.value : '';
  if (host !== 'www.${apex}') {
    return request;
  }

  var pairs = [];
  for (var key in request.querystring) {
    var entry = request.querystring[key];
    var values = entry.multiValue ? entry.multiValue : [entry];
    for (var i = 0; i < values.length; i++) {
      pairs.push(values[i].value === '' ? key : key + '=' + values[i].value);
    }
  }

  return {
    statusCode: 301,
    statusDescription: 'Moved Permanently',
    headers: {
      location: { value: 'https://${apex}' + request.uri + (pairs.length ? '?' + pairs.join('&') : '') },
    },
  };
}
