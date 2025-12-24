import React from "react";
import logo from "../../assets/logo-64x64.png"; // chemin vers ton logo

const NovaLogo = ({ size = 64 }) => {
  return (
    <img
      src={logo}
      alt="Nova Star Capital Logo"
      width={size}
      height={size}
      className="rounded-full"
    />
  );
};

export default NovaLogo;