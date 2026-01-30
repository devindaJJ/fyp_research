import { GoogleMap, LoadScript, Polyline, TrafficLayer, Marker } from "@react-google-maps/api";
import polyline from "@mapbox/polyline";

const containerStyle = {
  width: "100%",
  height: "300px",
};

const center = { lat: 6.9271, lng: 79.8612 }; // Colombo

const TrafficMap = ({ routes = [] }) => {

  const decodePolyline = (encoded) => {
    if (!encoded) return [];
    return polyline.decode(encoded).map(([lat, lng]) => ({ lat, lng }));
  };

  return (
    <LoadScript googleMapsApiKey={import.meta.env.VITE_GOOGLE_MAPS_API_KEY}>
      <GoogleMap mapContainerStyle={containerStyle} center={center} zoom={12}>

        <TrafficLayer autoUpdate />

        {routes.map((route, index) => (
          <Polyline
            key={index}
            path={decodePolyline(route.polyline)}
            options={{
              strokeColor: route.is_primary ? "#ff0000" : "#2251cc",
              strokeOpacity: 0.9,
              strokeWeight: 5,
            }}
          />
        ))}

      </GoogleMap>
    </LoadScript>
  );
};

export default TrafficMap;
