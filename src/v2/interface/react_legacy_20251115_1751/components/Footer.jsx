import React from "react";

const Footer = () => {
  return (
    <footer className="mt-10 text-center text-sm text-muted-foreground py-6 border-t border-border">
      <p>
        © {new Date().getFullYear()} Nova Star Capital. Tous droits réservés.
      </p>
    </footer>
  );
};

export { Footer };