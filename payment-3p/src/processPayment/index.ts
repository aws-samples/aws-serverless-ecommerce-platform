import { DocumentClient } from 'aws-sdk/clients/dynamodb';
const TABLE_NAME = process.env.TABLE_NAME || "TABLE_NAME";
const client = new DocumentClient();

// Generate a response for API Gateway
export function response(
        body: string | object,
        statusCode: number = 200,
        allowOrigin: string = "*",
        allowHeaders: string = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-requested-with",
        allowMethods: string = "GET,POST,PUT,DELETE,OPTIONS"
    ) {
    if (typeof body === "string") {
        body = { message: body };
    }
    return {
        statusCode: statusCode,
        body: JSON.stringify(body),
        headers: {
            "Access-Control-Allow-Headers": allowHeaders,
            "Access-Control-Allow-Origin": allowOrigin,
            "Access-Control-Allow-Methods": allowMethods
        }
    }
}

// Process paymentToken
export async function processPayment(client: DocumentClient, paymentToken: string) : Promise<boolean | null> {
    try {
        const response = await client.get({
            TableName: TABLE_NAME,
            Key: { paymentToken }
        }).promise();
        if (!response.Item)
            return false;

        await client.delete({
            TableName: TABLE_NAME,
            Key: { paymentToken }
        }).promise();
        return true;
    } catch (dbError) {
        console.log({"message": "Error processing the paymentToken from the database", "errormsg": dbError});
        return null;
    }
}

// Lambda function handler
export const handler = async (event: any = {}) : Promise <any> => {
    // Load body
    if (!event.body)
        return response("Missing body in event.", 400);
    const body = JSON.parse(event.body);

    // Validate body
    if (!body.paymentToken)
        return response("Missing 'paymentToken' in request body.", 400);
    if (typeof body.paymentToken !== "string")
        return response("'paymentToken' is not a string.", 400);

    // Check token
    const result = await exports.processPayment(client, body.paymentToken);
    if (result === null) {
        return response("Internal error", 500);
    } else {
        return response({"ok": result});
    }
}