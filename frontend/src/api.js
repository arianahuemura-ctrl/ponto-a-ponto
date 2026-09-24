export async function api(path, params, signal) {
  const response = await fetch(
    "/api/" + path + "/?" + new URLSearchParams(params),
    { signal },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || "Falha ao consultar o servidor.");
  return data;
}
export function getLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation)
      return reject(new Error("Seu navegador não oferece geolocalização."));
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ lat: coords.latitude, lon: coords.longitude }),
      (error) =>
        reject(
          new Error(
            error.code === 1
              ? "Permissão de localização negada. Informe um endereço."
              : "Não foi possível obter sua localização.",
          ),
        ),
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 30000 },
    );
  });
}
