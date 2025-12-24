import * as React from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";

const Slider = React.forwardRef(
  (
    {
      className = "",
      min = 0,
      max = 100,
      step = 1,
      value,
      defaultValue,
      onValueChange,
      disabled = false,
      // pour compat avec ton usage actuel (value/onChange numériques)
      onChange,
      ...props
    },
    ref
  ) => {
    // Normalise onChange(number) -> onValueChange([number])
    const handleValueChange = React.useCallback(
      (vals) => {
        onValueChange?.(vals);
        if (onChange && Array.isArray(vals) && typeof vals[0] === "number") {
          onChange(vals[0]);
        }
      },
      [onValueChange, onChange]
    );

    // Autorise value numérique ou tableau
    const normalizedValue =
      typeof value === "number" ? [value] : Array.isArray(value) ? value : undefined;
    const normalizedDefault =
      typeof defaultValue === "number"
        ? [defaultValue]
        : Array.isArray(defaultValue)
        ? defaultValue
        : [min];

    return (
      <SliderPrimitive.Root
        ref={ref}
        className={`relative flex w-full touch-none select-none items-center ${className}`}
        min={min}
        max={max}
        step={step}
        value={normalizedValue}
        defaultValue={normalizedDefault}
        onValueChange={handleValueChange}
        disabled={disabled}
        {...props}
      >
        <SliderPrimitive.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-muted">
          <SliderPrimitive.Range className="absolute h-full bg-primary" />
        </SliderPrimitive.Track>
        <SliderPrimitive.Thumb
          className="block h-4 w-4 rounded-full border border-primary bg-background ring-offset-background
                     transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
                     focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
        />
      </SliderPrimitive.Root>
    );
  }
);

Slider.displayName = "Slider";

export { Slider };
export default Slider;