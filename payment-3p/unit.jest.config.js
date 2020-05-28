module.exports = {
  collectCoverage: true,
  collectCoverageFrom: [
    "src/**/*.ts",
    "!**/node_modules/**",
    "!**/vendor/**"
  ],
  coverageThreshold: {
    "global": {
      "branches": 90,
      "functions": 90,
      "statements": 90
    }
  },
  reporters: [
    "default",
    ["jest-junit", {outputDirectory: "../reports/", outputName: `payment-3p-unit.xml`}]
  ],
  testMatch: [ '<rootDir>/tests/unit/**/*.test.ts'],
  transform: {
    "^.+\\.tsx?$": "ts-jest"
  },
}
