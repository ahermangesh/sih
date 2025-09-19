import * as React from "react"
import { cn } from "@/lib/utils"

const Tabs = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { defaultValue?: string; value?: string; onValueChange?: (value: string) => void }
>(({ className, children, defaultValue, value, onValueChange, ...props }, ref) => {
  const [selectedValue, setSelectedValue] = React.useState(defaultValue || '')
  
  const currentValue = value !== undefined ? value : selectedValue
  
  const handleValueChange = (newValue: string) => {
    if (value === undefined) {
      setSelectedValue(newValue)
    }
    onValueChange?.(newValue)
  }
  
  return (
    <div
      ref={ref}
      className={cn("w-full", className)}
      {...props}
    >
      {React.Children.map(children, child => 
        React.isValidElement(child) 
          ? React.cloneElement(child, { value: currentValue, onValueChange: handleValueChange } as any)
          : child
      )}
    </div>
  )
})
Tabs.displayName = "Tabs"

const TabsList = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "inline-flex h-10 items-center justify-center rounded-md bg-gray-100 p-1 text-gray-500",
      className
    )}
    {...props}
  >
    {children}
  </div>
))
TabsList.displayName = "TabsList"

const TabsTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { value: string; currentValue?: string; onValueChange?: (value: string) => void }
>(({ className, value, currentValue, onValueChange, children, ...props }, ref) => {
  const isSelected = currentValue === value
  
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        isSelected 
          ? "bg-white text-gray-900 shadow-sm" 
          : "text-gray-600 hover:text-gray-900",
        className
      )}
      onClick={() => onValueChange?.(value)}
      {...props}
    >
      {children}
    </button>
  )
})
TabsTrigger.displayName = "TabsTrigger"

const TabsContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { value: string; currentValue?: string }
>(({ className, value, currentValue, children, ...props }, ref) => {
  if (currentValue !== value) return null
  
  return (
    <div
      ref={ref}
      className={cn(
        "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
})
TabsContent.displayName = "TabsContent"

// Enhanced versions that work with the context
const EnhancedTabsList = ({ children, ...props }: any) => (
  <TabsList {...props}>
    {React.Children.map(children, child => 
      React.isValidElement(child) 
        ? React.cloneElement(child, { currentValue: props.value, onValueChange: props.onValueChange } as any)
        : child
    )}
  </TabsList>
)

const EnhancedTabsContent = ({ children, ...props }: any) => (
  <TabsContent {...props} currentValue={props.value}>
    {children}
  </TabsContent>
)

export { 
  Tabs, 
  EnhancedTabsList as TabsList, 
  TabsTrigger, 
  EnhancedTabsContent as TabsContent 
}