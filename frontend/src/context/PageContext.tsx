"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

type EntityContext = {
  type: string;
  id: string | number;
};

export type PageContextData = {
  page: string;
  entity?: EntityContext;
  active_invoice?: string | number;
  date_filter?: string;
};

interface PageContextType {
  pageContext: PageContextData;
  setPageContext: React.Dispatch<React.SetStateAction<PageContextData>>;
}

const defaultContextData: PageContextData = {
  page: "Home",
  date_filter: "This Month"
};

const PageContext = createContext<PageContextType>({
  pageContext: defaultContextData,
  setPageContext: () => {},
});

export const PageProvider = ({ children }: { children: ReactNode }) => {
  const [pageContext, setPageContext] = useState<PageContextData>(defaultContextData);

  return (
    <PageContext.Provider value={{ pageContext, setPageContext }}>
      {children}
    </PageContext.Provider>
  );
};

export const usePageContext = () => {
  const context = useContext(PageContext);
  if (!context) {
    throw new Error("usePageContext must be used within a PageProvider");
  }
  return context;
};
