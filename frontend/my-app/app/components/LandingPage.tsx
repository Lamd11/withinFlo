'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import UrlForm from './UrlForm';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: 'spring',
      stiffness: 100,
      damping: 12,
    },
  },
};

const floatingAnimation = {
  y: ['-4px', '4px'],
  transition: {
    y: {
      duration: 2,
      repeat: Infinity,
      repeatType: 'reverse',
      ease: 'easeInOut',
    },
  },
};

interface LandingPageProps {
  onSubmit: (url: string, auth: any, context: any) => void;
  isLoading: boolean;
}

export default function LandingPage({ onSubmit, isLoading }: LandingPageProps) {
  const features = [
    {
      title: 'AI-Powered Analysis',
      description: 'Our advanced AI analyzes websites and generates comprehensive test cases automatically.',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      ),
    },
    {
      title: 'Time-Saving',
      description: 'Reduce documentation time by up to 80% with automatically generated test documentation.',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      title: 'Comprehensive Reports',
      description: 'Get detailed test cases, scenarios, and documentation in markdown and JSON formats.',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      <motion.div 
        className="container mx-auto px-4 py-16"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Hero Section */}
        <div className="text-center mb-20">
          <motion.div 
            className="inline-block mb-6"
            animate={floatingAnimation}
          >
            <div className="flex justify-center">
              <div className="relative">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full blur opacity-75"></div>
                <div className="relative bg-white dark:bg-gray-800 rounded-full p-4">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
              </div>
            </div>
          </motion.div>
          
          <motion.h1 
            className="text-5xl md:text-6xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600"
            variants={itemVariants}
          >
            withinFlo
          </motion.h1>
          
          <motion.h2 
            className="text-2xl md:text-3xl font-bold text-gray-800 dark:text-white mb-6"
            variants={itemVariants}
          >
            AI-Powered QA Documentation Generator
          </motion.h2>
          
          <motion.p 
            className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto mb-10"
            variants={itemVariants}
          >
            Transform the way you create test documentation. Our AI analyzes your websites and automatically generates comprehensive test cases, saving you hours of manual work.
          </motion.p>
          
          <motion.div 
            variants={itemVariants}
            className="mb-12"
          >
            <motion.a
              href="#url-form"
              className="inline-flex items-center px-6 py-3 text-lg font-medium text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-full shadow-lg hover:shadow-xl transform transition-all duration-300 hover:scale-105"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Get Started Now
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 ml-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </motion.a>
          </motion.div>
        </div>

        {/* Features Section */}
        <motion.div 
          className="grid md:grid-cols-3 gap-10 mb-20"
          variants={containerVariants}
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 transform transition-all duration-300 hover:-translate-y-2 hover:shadow-xl"
              variants={itemVariants}
              whileHover={{ scale: 1.03 }}
            >
              <div className="mb-4">{feature.icon}</div>
              <h3 className="text-xl font-bold mb-2 text-gray-800 dark:text-white">{feature.title}</h3>
              <p className="text-gray-600 dark:text-gray-300">{feature.description}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* URL Form Section */}
        <motion.div 
          id="url-form"
          variants={itemVariants}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden transform transition-all duration-500 hover:shadow-indigo-500/10 dark:hover:shadow-indigo-500/20"
          whileHover={{ 
            boxShadow: "0 0 20px rgba(99, 102, 241, 0.2)"
          }}
        >
          <div className="p-1">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-t-xl p-6">
              <h2 className="text-2xl font-bold text-white">Enter Website URL</h2>
              <p className="text-indigo-100">Our AI will analyze the website and generate test documentation</p>
            </div>
            
            <div className="p-6">
              <UrlForm onSubmit={onSubmit} isLoading={isLoading} />
            </div>
          </div>
        </motion.div>

        {/* Bottom Section with Animation */}
        <motion.div 
          className="mt-24 text-center"
          variants={itemVariants}
        >
          <p className="text-gray-600 dark:text-gray-400 mb-6">Trusted by QA teams worldwide</p>
          
          <div className="flex justify-center space-x-12 opacity-70">
            {[1, 2, 3, 4, 5].map((i) => (
              <motion.div 
                key={i}
                className="w-24 h-12 bg-gray-200 dark:bg-gray-700 rounded-md"
                animate={{
                  opacity: [0.5, 0.8, 0.5],
                  transition: {
                    duration: 2 + (i * 0.5),
                    repeat: Infinity,
                  }
                }}
              ></motion.div>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
} 